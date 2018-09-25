from flask import Flask, request,abort
from flask_restful import Api, Resource, reqparse
import requests
from requests.auth import HTTPBasicAuth
import urllib3
urllib3.disable_warnings()
import arrow
from infinisdk import InfiniBox
#https://flask-restful.readthedocs.io/en/0.3.5/quickstart.html


app = Flask(__name__)
api = Api(app)

ibox = "192.168.0.30"
cred=('admin', '123456')
creds = HTTPBasicAuth('admin', '123456')
system=InfiniBox(ibox,cred)
system.login()
onegig = 1000000000
id_str="546c4f25-FFFF-FFFF-ab9c-34306c4"
date_format='YYYY-MM-DD HH:mm:ss'
id_len=5

new_size = lambda  size: size/1024/1024/1024 
def new_date(date):
	print "Date is {}".format(date)
	tsa=arrow.get(str(date)[:-3])
	return tsa.format(date_format)

def set_new_id(id):
	embedding_zeros=id_len-len(str(id))
	new_id=id_str+embedding_zeros*"0"+str(id)
	return new_id

def add_metadata(vol_json):
	vol_id=vol_json['result']['id']
	vol_obj_list=system.volumes.find(id=vol_id).to_list()
	if vol_obj_list:
		vol_obj=vol_obj_list[0]
		metadata=vol_obj.get_all_metadata()
		for key in metadata.keys():
			vol_json['result'][key]=metadata[key]
	return vol_json
	

def poolselect():
    url="http://{}/api/rest/pools".format(ibox)
    pools = requests.get(url=url,auth=creds)
    return pools.json()['result'][-1]

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
        url="http://{}/api/rest/volumes".format(ibox)
        #outp = requests.get(url=url,auth=HTTPBasicAuth('iscsi', '123456')).json()['result']
        outp = requests.get(url=url,auth=creds)
        return outp.json(), int(outp.status_code)
    def post(self):
        url="http://{}/api/rest/volumes".format(ibox)
        args = self.reqparse.parse_args()
        vol = {
            'pool_id': args['pool_id'],
            'name': args['name'],
            'provtype': args['provtype'],
            'size': args['size']*onegig
        }
        outp = requests.post(url=url,json=vol, auth=creds)
        return outp.text, int(outp.status_code)

class Volume(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        #self.reqparse
    def get(self, id):
        #url="http://{}/api/rest/volumes/{}".format(ibox, id)
        url="http://{}/api/rest/volumes/{}".format(ibox, id)
        outp = requests.get(url=url,auth=creds)
	outp_json = outp.json()
	outp_json=add_metadata(outp_json)
	outp_json['result']['id'] = set_new_id(outp_json['result']['id'])
	outp_json['result']['size'] = new_size(int(outp_json['result']['size']))
	outp_json['result']['create_at'] = new_date(int(outp_json['result']['created_at']))
        #return outp.json(), int(outp.status_code)
        return outp_json, int(outp.status_code)
        
    def post(self, id):

        string="id is {}".format(id)
        return string
    def put(self, id):
        body=request.json
        string="id is {} data is {}".format(id, body)
        return string,400
    def delete(self, id):
        url="http://{}/api/rest/volumes/{}?approved=yes".format(ibox, id)
        outp = requests.delete(url=url,auth=creds)
        return outp.json(), int(outp.status_code)

api.add_resource(VolumesList, "/api/v1/volumes")
api.add_resource(Volume, "/api/v1/volumes/<int:id>")
app.run(debug=True, port=8080, host='0.0.0.0')
    
