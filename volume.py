from flask import Flask, request,abort,jsonify
from flask_restful import Api, Resource, reqparse
import requests
from requests.auth import HTTPBasicAuth
import urllib3
urllib3.disable_warnings()
import arrow
from infinisdk import InfiniBox
from capacity import GB,GiB

import time
import random, string
import json
import subprocess
from infi.dtypes.iqn import make_iscsi_name
from time import gmtime, strftime

#https://flask-restful.readthedocs.io/en/0.3.5/quickstart.html

## V2 - Volume functions
def get_host(system,host_name):
    name=host_name.replace(':','%')
    host=system.hosts.find(name=name).to_list()
    if host:
        return host[0]
    else:
        address=make_iscsi_name(host_name)
        host=system.hosts.create(name=name)
        host.add_port(address)
        return host

def check_iqn_logged_in(system,iqn):
    initators=system.initiators.to_list()
    print "initators: {}".format(initators)
    for init in initators:
        if init['address'] == iqn:
            return False
    return True

class InvalidUsage(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv

app = Flask(__name__)
api = Api(app)


## To be replaced with the actual values
loggedout_attempts=3
loggedout_interval=3
ibox = "192.168.0.30"
notify_dir = '/tmp/'
notify_log = notify_dir+ "notify.log"
notify_script = "./notify_rm.sh"
cred=('admin', '123456')
creds = HTTPBasicAuth('admin', '123456')

### InfiniSDK Par/t
#Creds=HTTPBasicAuth(cred)
system=InfiniBox(ibox,cred)
system.login()
pool=system.pools.to_list()[0]
###
# Constants
onegig = 1000000000
id_str="546c4f25-FFFF-FFFF-ab9c-34306c4"
service_id='d4a44b0a-e3c2-4fec-9a3c-1d2cb14328f9'
date_format='YYYY-MM-DD HH:mm:ss'
id_len=5
opts_pars = { 'volume_type': '' , 'iscsi_init': '', 'image_id': '', 'bootable': 0, 'zone_code': 0}
#iscsi_init=''
mandatory_pars = ['name','size']
vol_name_length=10


## Functions
generate_random_name=lambda length: ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))
ts=lambda now: strftime("%Y-%m-%d %H:%M:%S", gmtime())
new_size = lambda  size: size/1000/1000/1000 
def new_date(date):
	print "Date is {}".format(date)
	tsa=arrow.get(str(date)[:-3])
	return tsa.format(date_format)

def set_new_id(id):
	embedding_zeros=id_len-len(str(id))
	new_id=id_str+embedding_zeros*"0"+str(id)
	return new_id
def notify_rm(file):
	try:
		return subprocess.Popen([notify_script,file])
	except Exception as E:
		notify_log_file=open(notify_log,'w')
		notify.write("Failed to call notify, {}".fomrat(E))

def add_metadata_old(vol_json):
    ret_dict={}
    vol_id=vol_json['result']['id']
    vol_obj_list=system.volumes.find(id=vol_id).to_list()
    if vol_obj_list:
        vol_obj=vol_obj_list[0]
        metadata=vol_obj.get_all_metadata()
        for key in metadata.keys():
            ret_dict[key]=metadata[key]
    return ret_dict
	
def add_metadata(volume):
    ret_dict={}
    metadata=volume.get_all_metadata()
    for key in metadata.keys():
        ret_dict[key]=metadata[key]
    return ret_dict


def poolselect():
    url="http://{}/api/rest/pools".format(ibox)
    pools = requests.get(url=url,auth=creds)
    return pools.json()['result'][-1]

def get_vol_data_old(vol_data,vol_id):
    return_json={}
    return_json['volumes']={}
    return_json['volumes'].update(add_metadata(vol_data))
    #return_json['id'] = set_new_id(outp_json['result']['id'])
    return_json['volumes']['id'] = vol_id
    return_json['volumes']['size'] = new_size(int(vol_data['result']['size']))
    return_json['volumes']['create_at'] = new_date(int(vol_data['result']['created_at']))
    #return_json['volumes']['name'] = vol_data['result']['name']
    return_json['volumes']['lun_id'] = vol_data['result']['id']
    #return_json['volumes']['iscsi_init'] = vol_data['result']['serial']
    #return_json['volumes']['iscsi_init'] = iscsi_init
    #return_json['volumes']['iscsi_init'] = iscsi_init
    return_json['volumes']['service_id'] = service_id
    return_json['volumes']['status'] = 'available'
    if vol_data['result']['mapped']:
        return_json['volumes']['attach_status'] = 'online'
    else:
        return_json['volumes']['attach_status'] = 'offline'
    return 


def get_vol_data(volume):
    return_json={}
    return_json['volumes']={}
    #ITAI 08/11/2018 return_json['volumes'].update(add_metadata(vol_data))
    return_json['volumes'].update(add_metadata(volume))
    #return_json['id'] = set_new_id(outp_json['result']['id'])
    return_json['volumes']['id'] = set_new_id(volume.get_id())
    return_json['volumes']['size'] = new_size(volume.get_size().bits/8/1024/1024/1024)
    return_json['volumes']['create_at'] = volume.get_created_at().format('YYYY-MM-DD HH:mm:ss')
    #return_json['volumes']['name'] = vol_data['result']['name']
    return_json['volumes']['lun_id'] = volume.get_id()
    #return_json['volumes']['iscsi_init'] = vol_data['result']['serial']
    #return_json['volumes']['iscsi_init'] = iscsi_init
    #return_json['volumes']['iscsi_init'] = iscsi_init
    return_json['volumes']['service_id'] = service_id
    return_json['volumes']['status'] = 'available'
    if volume.is_mapped():
        return_json['volumes']['attach_status'] = 'online'
    else:
        return_json['volumes']['attach_status'] = 'offline'
    return return_json

class VolumesList(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('pool_id', type=int, required=False, location='json',default=poolselect()['id'])
        self.reqparse.add_argument('name', type=str, required=True, location='json')
        self.reqparse.add_argument('provtype', type=str, required=False, location='json', default='THIN')
        self.reqparse.add_argument('size', type=int, required=True, location='json')
        super(VolumesList, self).__init__()
    def get(self):
        #url="http://{}/api/rest/volumes/{}".format(ibox, id)
        #url="http://{}/api/rest/volumes".format(ibox)
        #outp = requests.get(url=url,auth=HTTPBasicAuth('iscsi', '123456')).json()['result']
        outp=[]
        volumes=system.volumes.to_list()
        for volume in volumes:
            #print outp
            cur_vol=get_vol_data(volume)
            outp.append(cur_vol)
        print outp
        return outp,'200'
    def post(self):
        #url="http://{}/api/rest/volumes".format(ibox)
        #args = self.reqparse.parse_args(
        #vol = {
        #    'pool_id': args['pool_id'],
        #    'name': args['name'],
        #    'provtype': args['provtype'],
        #    'size': args['size']*onegig
        #}
        #outp = requests.post(url=url,json=vol, auth=creds)
        body=request.json

        #print "this is body {}".format(body)
        for mandatory_key in mandatory_pars:
            if mandatory_key not in body['volumes']: ##1
                print "mandatory_key {} can't be found".format(mandatory_key)
                raise InvalidUsage('Mandatory key cannot be found', status_code=410)
        try:
            #print "Creating a volume, size {}, name {}".format(body['size'],body['name'])
            new_name=generate_random_name(vol_name_length)
            #volume=system.volumes.create(pool=pool,size=body['size']*GB,name=body['name'])
            volume=system.volumes.create(pool=pool,size=body['volumes']['size']*GB,name=new_name)
        except Exception as E:
        
            raise InvalidUsage('Error Caught {}'.format(E), status_code=420)
        volume.set_metadata('name',body['volumes']['name'])
        ## Itai ISCSI INIT SET
        volume.set_metadata('iscsi_init',body['volumes']['iscsi_init'])
        for optional_key in opts_pars:
            if optional_key in body['volumes']:
                volume.set_metadata(optional_key,body['volumes'][optional_key])
            else:
                volume.set_metadata(optional_key,opts_pars[optional_key])
        vol_new_id=set_new_id(volume.get_id())
        notify=notify_dir+vol_new_id
        url="http://{}/api/rest/volumes/{}".format(ibox,volume.get_id())
        vol_infi_data=requests.get(url=url,auth=creds)
        #print "INFI DATA****** {}".format(vol_infi_data)
        global iscsi_init
        global volume_type
        if 'iscsi_init' in body['volumes'].keys():
            iscsi_init=body['volumes']['iscsi_init']
        else:
            iscsi_init=''
        #if 'volume_type' in body['volumes'].keys():
        #    volume_type=body['volumes']['volume_type']
        #else:
        #    volume_type=''
        #ITAI 08/11/18 vol_data=get_vol_data(vol_infi_data.json(), vol_new_id)
        vol_data=get_vol_data(volume)
        notify_vol={}
        notify_vol={"snapshot_id":"", "notify_type":"volume_create","status":"available","result":"success"}
        notify_vol['volume_id'] = vol_new_id
        notify_vol['create_at'] = vol_data['volumes']['create_at']
        try:
            #print "notify is {}".format(notify)
            notify_f=open(notify,'w')
            notify_f.writelines(json.dumps(notify_vol))
            notify_f.close()
            notify_rm(notify)
        except Exception as E:
            str="Failed! {}".format(E)
        #print str
            return str,400
	vol_data['volumes']['status']='creating'
        return vol_data, 200

class Volume(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        #self.reqparse
    def get(self, vol_id):
        #url="http://{}/api/rest/volumes/{}".format(ibox, id)
        infi_id=vol_id[-5:]
        #url="http://{}/api/rest/volumes/{}".format(ibox, infi_id)
        #print "URL IS {}".format(url)
        #outp = requests.get(url=url,auth=creds)
        #outp_json = outp.json()
        try:
            volume=system.volumes.find(id=infi_id)[0]
        except Exception: #outp_json['error'] or not outp_json['result']:
            return {},'404'
        #ITAI 08/11/2018 return_json=get_vol_data(outp_json,vol_id)
        return_json=get_vol_data(volume)
        #return outp.json() int(outp.status_code)
        return return_json, '200'
        
    def post(self, id):
       pass

    def put(self, id):
        body=request.json
	print type(body)
	print body.keys()
        string="id is {} data is {}".format(id, body)
        return string,400
    def delete(self, vol_id):
        notify=notify_dir+vol_id
        infi_vol_id=int(vol_id[-5:])
        #print "*** VOL ID IS {}".format(vol_id)
        #ITAI 08/11/2018
        #url="http://{}/api/rest/volumes/{}?approved=yes".format(ibox, infi_vol_id)
        #print "URL IS {}".format(url)
        try:
            #outp = requests.delete(url=url,auth=creds)
            volume=system.volumes.find(id=infi_vol_id)
            vol_data=get_vol_data(volume)
            volume.delete()
        except Exception as E:
            print E
            abort(500)
        #ITAI 08/11/2018 vol_data=get_vol_data(outp.json(),vol_id)
        ret_data={}
        #ret_data['volume_id']=vol_data['volumes']['id']
        ret_data['volume_id']=vol_id
        ret_data['create_at']=vol_data['volumes']['create_at']
        ret_data['status']='deleted'
        ret_data['result']='success'
        ret_data['snapshot_id']=""
        ret_data['notify_type']='volume_delete'
        try:
        	print "notify is {}".format(notify)
	    	notify_f=open(notify,'w')
	    	notify_f.writelines(json.dumps(ret_data))
	    	notify_f.close()
	    	notify_rm(notify)
	except Exception:
	    	pass
        #print str
        #return "kuku",200
        time.sleep(5)
        return ret_data, int(outp.status_code)
class VolumesAttachment(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()

    def post(self):
        body=request.json
        status='success'
        host=get_host(system,body['volume']['iscsi_init'])
        for volume in body['volume']['volumes']:
            vol=system.volumes.find(id=volume['volume_id'][-5:]).to_list()
            if not vol:
                pass
            if body['volume']['action'].upper() == "ATTACH":
                try: 
                    host.map_volume(vol[0],lun=volume['order'])
                except Exception as E:
                    print "Execption {}".format(E)
                    status='fail'
            elif body['volume']['action'].upper() == "DETACH":
                ## TASK - Add tests here to find if volume is 'in use'
                for attempt in xrange(loggedout_attempts):
                    val=check_iqn_logged_in(system,body['volume']['iscsi_init'])
                    print "val is {}".format(val)
                    if val:
                         print "unmapping {} which is {}".format(vol[0],type(vol[0]))
                         host.unmap_volume(vol[0])
                         status='success'
                         break
                    else:
                        time.sleep(loggedout_interval)
                        print "Host is still online"
                        status='fail'
            else:
                status='fail'

        body['status']=status
        return body,200 ## change ret codes

class VolumeExpand(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()

    def post(self,vol_id):
        body=request.json
        print "body is {}".format(body)
        print "id is {}".format(vol_id)
        #volume=body['volume']['volume_id']
        volume=vol_id
        new_size=body['volume']['size']

        volume_object=system.volumes.find(id=vol_id[-5:]).to_list()
        if not volume_object:
            return 404,"Volume not found"
        volume_size=volume_object[0].get_size().bits/8/1024/1024/1024
        if volume_size > new_size:
            return 405,"Volume is already bigger"
        cap_to_resize=(new_size-volume_size)*GB
        try:
            volume_object[0].resize(cap_to_resize)
        except Exception as E:
            print "Caught Exception {}".format(E)
            return 500,"Exception"
        ret_data={}
        #ret_data['volume_id']=vol_data['volumes']['id']
        ret_data['volume_id']=vol_id
        ret_data['snapshot_id']=''
        ret_data['status']='available'
        ret_data['result']='success'
        ret_data['snapshot_id']=""
        ret_data['notify_type']='volume_extend'
        ret_data['create_at']=ts("now")
        try:
            print "notify is {}".format(notify)
            notify_f=open(notify,'w')
            notify_f.writelines(json.dumps(ret_data))
            notify_f.close()
            notify_rm(notify)
        except Exception:
            pass
        return 200,"success"
    
api.add_resource(VolumesList, "/api/v1/volumes")
api.add_resource(VolumesAttachment, "/api/v1/volumes/attachment")
api.add_resource(Volume, "/api/v1/volumes/<string:vol_id>")
api.add_resource(VolumeExpand, "/api/v1/volumes/<string:vol_id>/expand")
app.run(debug=True, port=8080, host='0.0.0.0')
    
