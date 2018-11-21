from flask import Flask, request,abort,jsonify
from flask_restful import Api, Resource, reqparse
import requests
from requests.auth import HTTPBasicAuth
import urllib3
urllib3.disable_warnings()
import arrow
from infinisdk import InfiniBox
from capacity import GB,GiB
from zone import *
import time
import random, string
import json
import subprocess
from infi.dtypes.iqn import make_iscsi_name
from time import gmtime, strftime
zone_file='./zones.json'

global zoneset
zoneset=get_zones_data(zone_file)
set_box_hexa(zoneset)
#try:
#    box_login(zoneset)
#except Exception as E:
    #logging.error("unable to login to infinibox, aborting {}".format(E))
#    print E
#    exit(5)

### Wrapper 
def loggin_in_out(func):
    def wrapper(*args,**kwargs):
        box_login(zoneset,'login')
        return func(*args,**kwargs)
        #print "logging out"
        box_login(zoneset,'logout')
    return wrapper

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
    #print "initators: {}".format(initators)
    for init in initators:
        if init.get_address() == iqn:
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
#ITAI 08112018
#system=InfiniBox(ibox,cred)
#system.login()
#pool=system.pools.to_list()[0]
#ITAI 08112018
###
# Constants
onegig = 1000000000
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
	#print "Date is {}".format(date)
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

	
def add_metadata(volume):
    ret_dict={}
    metadata=volume.get_all_metadata()
    for key in metadata.keys():
        ret_dict[key]=metadata[key]
    return ret_dict



def get_vol_data(volume):
    return_json={}
    return_json['volumes']={}
    return_json['volumes'].update(add_metadata(volume))
    #return_json['volumes']['id'] = set_new_id(volume.get_id())
    #return_json['volumes']['id']=encode_vol_by_id(val=volume)
    return_json['volumes']['size'] = volume.get_size().bits/8/1000000000
    return_json['volumes']['create_at'] = volume.get_created_at().format('YYYY-MM-DD HH:mm:ss')
    return_json['volumes']['lun_id'] = volume.get_id()
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
        #self.reqparse.add_argument('pool_id', type=int, required=False, location='json',default=poolselect()['id'])
        self.reqparse.add_argument('name', type=str, required=True, location='json')
        self.reqparse.add_argument('provtype', type=str, required=False, location='json', default='THIN')
        self.reqparse.add_argument('size', type=int, required=True, location='json')
        super(VolumesList, self).__init__()
   
    @loggin_in_out
    def get(self):
        outp=[]
        return_json={}
        ## ITAI 081118
        if 'iscsi_init' in request.args:
            iscsi_filter=request.args['iscsi_init']
        else:
            iscsi_filter=False
        volumes=[]
        for box in zoneset['zones']:
            print "box is {}".format(box['ibox'])
            volumes.extend(box['ibox'].volumes.to_list())
        #volumes=system.volumes.to_list()
        
        for volume in volumes:
            if iscsi_filter and 'iscsi_init' in volume.get_all_metadata().keys() and volume.get_metadata_value('iscsi_init') != iscsi_filter:
                continue 
            else: 
               # print "vol is {}".format(volume.get_name())
                cur_vol=get_vol_data(volume)
                #print "cur vol is {} and its type is {}".format(cur_vol,type(cur_vol))
                #print "*******"
                #print len(outp)
                outp.append(cur_vol['volumes'])
        ## ITAI 081118
        #print outp
        return_json['volumes']=outp
        return return_json,'200'
    
    @loggin_in_out
    def post(self):

        #body=request.json
        body=request.json
        for mandatory_key in mandatory_pars:
            if mandatory_key not in body['volumes']: ##1
                print "mandatory_key {} can't be found".format(mandatory_key)
                raise InvalidUsage('Mandatory key cannot be found', status_code=410)
        #try:
            ## ITAI 081118
 	#print "zoneset {} looking for {}".format(zoneset,body['volumes']['zone_code'])
        system=get_box_by_par(par="name",req="ibox",val=body['volumes']['zone_code'],zones=zoneset)
        #print "******* found {}".format(system.get_name())
        pool=system.pools.to_list()[0]
        #print "system is {}, pool is {}".format(system.get_name(),pool.get_name())
        if not system:
            return '',404
            ## ITAI 081118
        new_name=generate_random_name(vol_name_length)
        volume=system.volumes.create(pool=pool,size=body['volumes']['size']*GB,name=new_name)
        #except Exception as E:
        ##    print "exception is {}".format(E)
        #    raise InvalidUsage('Error Caught {}'.format(E), status_code=420)
        volume.set_metadata('name',body['volumes']['name'])
        volume.set_metadata('iscsi_init',body['volumes']['iscsi_init'])
        new_id=encode_vol_by_id(val=system,id=volume.get_id(),type='ibox',zones=zoneset)
        #print ">>>> new id is {}".format(new_id)
        volume.set_metadata('id',new_id)
        for optional_key in opts_pars:
            if optional_key in body['volumes']:
                volume.set_metadata(optional_key,body['volumes'][optional_key])
            else:
                volume.set_metadata(optional_key,opts_pars[optional_key])
        ## ITAI 081118
        #vol_new_id=set_new_id(volume.get_id())
        #vol_new_id=encode_vol_by_id(val=system.get_serial(),id=volume.get_id(),type='serial_dec')
        #print "new id: {}".format(vol_new_id)
        ## ITAI 081118
        notify=notify_dir+new_id
        url="http://{}/api/rest/volumes/{}".format(system.get_name(),volume.get_id())
        #print "url is {}".format(url)
        vol_infi_data=requests.get(url=url,auth=creds)
        global iscsi_init
        global volume_type
        if 'iscsi_init' in body['volumes'].keys():
            iscsi_init=body['volumes']['iscsi_init']
        else:
            iscsi_init=''
        #print "getting vol data"
        vol_data=get_vol_data(volume)
        #print "vol data is {}".format(vol_data)
        notify_vol={}
        notify_vol={"snapshot_id":"", "notify_type":"volume_create","status":"available","result":"success"}
        #notify_vol['volume_id'] = vol_new_id
        notify_vol['volume_id']=new_id
        notify_vol['create_at'] = vol_data['volumes']['create_at']
        try:
            notify_f=open(notify,'w')
            notify_f.writelines(json.dumps(notify_vol))
            notify_f.close()
            notify_rm(notify)
	    print "got until here"
        except Exception as E:
            str="Failed! {} ; notify is {}".format(E,notify)
            print str 		
            #return str,400
	vol_data['volumes']['status']='creating'
        return vol_data, 200

class Volume(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
    

    @loggin_in_out
    def get(self, vol_id):

        #ITAI 08112018

        ###infi_id=vol_id[-5:]
        system,vol=decode_vol_by_id(vol_id,'ibox',zoneset)
        #ITAI 08112018
        try:
            #print "looking on {} for {}".format(system.get_name(), vol)
            volume=system.volumes.find(id=vol)[0]
        except Exception: #outp_json['error'] or not outp_json['result']:
            return {},'404'
        #print "found vol {}".format(vol.get_name())
        return_json=get_vol_data(volume)
        return return_json, '200'
        
    def post(self, id):
       pass

    def put(self, id):
        body=request.json
	#print type(body)
	print body.keys()
        string="id is {} data is {}".format(id, body)
        return string,400
    
    @loggin_in_out
    def delete(self, vol_id):
        notify=notify_dir+vol_id
        #print "in volume deletion"
        #ITAI 08112018
        ###infi_vol_id=int(vol_id[-5:])
        system,vol=decode_vol_by_id(vol_id,'ibox',zoneset)
        #print "for deletion - volume {} in box {}".format(int(vol),system)
        try:
            volume=system.volumes.find(id=int(vol))
            #print "found for deletion {}".format(volume.get_id())
            if volume:
                vol_data=get_vol_data(volume[0])
                volume[0].delete()
            else: 
                return {},'200'
        except Exception as E:
            print E
            abort(500)
        ret_data={}
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
        time.sleep(5)
        return ret_data, '200'
class VolumesAttachment(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()

    @loggin_in_out    
    def post(self):
        body=request.json
        status='success'
        #ITAI 08112018
        ###host=get_host(system,body['volume']['iscsi_init'])
        for volume in body['volume']['volumes']:
            #ITAI 08112018
            system,vol_inf_id=decode_vol_by_id(volume['volume_id'],'ibox',zoneset)
            host=get_host(system,body['volume']['iscsi_init'])
            #ITAI 08112018
            vol=system.volumes.find(id=vol_inf_id).to_list()
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
                    #print "val is {}".format(val)
                    if val:
                         #print "unmapping {} which is {}".format(vol[0],type(vol[0]))
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
    
    @loggin_in_out        
    def post(self,vol_id):
        body=request.json
        #print "body is {}".format(body)
        #print "id is {}".format(vol_id)
        #volume=body['volume']['volume_id']
        volume=vol_id
        new_size=int(body['volume']['size'])
        #ITAI 08112018
        system,vol_inf_id=decode_vol_by_id(vol_id,'ibox',zoneset)
        volume_object=system.volumes.find(id=vol_inf_id).to_list()
        if not volume_object:
            return 404,"Volume not found"
        volume_size=volume_object[0].get_size().bits/8/1000000000
        #print "volume size is {} new size is {}".format(volume_size,new_size)
        if volume_size > new_size:
            return 405,"Volume is already bigger"
        cap_to_resize=(new_size-volume_size)*GB
        try:
            volume_object[0].resize(cap_to_resize)
        except Exception as E:
            print "Caught Exception {}".format(E)
            return 500,"Exception"
        ret_data={}
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
    
#api.add_resource(VolumesList, "/api/v1/volumes")
#api.add_resource(VolumesAttachment, "/api/v1/volumes/attachment")
#api.add_resource(Volume, "/api/v1/volumes/<string:vol_id>")
#api.add_resource(VolumeExpand, "/api/v1/volumes/<string:vol_id>/expand")
#app.run(debug=True, port=8080, host='0.0.0.0')
    
