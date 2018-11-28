from flask import Flask, request
from flask_restful import Api, Resource, reqparse
import requests
from requests.auth import HTTPBasicAuth
import urllib3
from zone import zones,  get_box_by_par
urllib3.disable_warnings()

# need to add relevant changes to URLs when quering for zone_code
openstack='192.168.0.3'
glanceport='9292'

def format_image(data):
    todict = {
        "zone_code":'zonecode1',
        "id":data['id'],
        "name":data['name'],
        "status":data['status'],
        "size":data['size'],
        "created_at":data['created_at'],
        "format":data['disk_format'],
        "visibility":data['visibility'],
        "type":'Image'
    }
    if 'zone_code' in request.args:
        todict["zone_code"]=request.args['zone_code']
    return todict

class ImagesList(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('ServiceCode', type=str, required=True, location='headers')
        self.reqparse.add_argument('ServiceKey', type=str, required=True, location='headers')
        # self.reqparse.add_argument('zone_code', type=str, required=True, location='json')
        self.reqparse.add_argument('name', type=str, required=False, location='json')
        super(ImagesList, self).__init__()
    def get(self):
        reqargs = self.reqparse.parse_args()
        if 'zone_code' in request.args:
            openstack=get_box_by_par(par='name', val=request.args['zone_code'] , req='openstack_glance',zones=zones)
            url="http://{}:{}/v2/images".format(openstack, glanceport)
            if 'name' in request.args:
                url="http://{}:{}/v2/images?name={}".format(openstack, glanceport, request.args['name'])
            reqargs = self.reqparse.parse_args()
            headers = {'X-Auth-Token': reqargs['ServiceKey']}
            outp = requests.get(url=url,headers=headers)
	    if outp.status_code == 200:
	            image_list=[]
        	    for item in outp.json()['images']:
                	    image_list.append(format_image(item))
	            image_dict = {"images":image_list}
        	    return image_dict, 200
	    else:
		return outp.reason, outp.status_code
        else:
	     openstack='192.168.0.3'
             reqargs = self.reqparse.parse_args()
             #for zone in zones['zones']:
             url="http://{}:{}/v2/images".format(openstack, glanceport)
	     if 'name' in request.args:
                 url="http://{}:{}/v2/images?name={}".format(openstack, glanceport, request.args['name'])
	     headers = {'X-Auth-Token': reqargs['ServiceKey']}
             outp = requests.get(url=url,headers=headers)
	     if outp.status_code == 200:
	         image_list=[]
                 for item in outp.json()['images']:
                        image_list.append(format_image(item))
                 image_dict = {"images":image_list}
                 return image_dict, 200 
	     else:
		return outp.reason, outp.status_code

    

class Image(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('ServiceCode', type=str, required=True, location='headers')
        self.reqparse.add_argument('ServiceKey', type=str, required=True, location='headers')
        # self.reqparse.add_argument('zone_code', type=str, required=True, location='json')
        super(Image, self).__init__()
    def get(self, reqid):
        reqargs = self.reqparse.parse_args()
        if 'zone_code' in request.args:
            openstack=get_box_by_par(par='name', val=request.args['zone_code'] , req='openstack_glance', zones=zones)
        url="http://{}:{}/v2/images/{}".format(openstack, glanceport, reqid)
        headers = {'X-Auth-Token': reqargs['ServiceKey']}
        outp = requests.get(url=url,headers=headers)
	if outp.status_code == 200:
	        fimage=format_image(outp.json())
        	image_dict = {"image":fimage}
	        return image_dict, 200
	else:
		return outp.reason, outp.status_code
    

#api.add_resource(ImagesList, "/api/v1/images")
#api.add_resource(Image, "/api/v1/images/<reqid>")
#if __name__ == '__main__':
#    app.run(debug=True, port=8080)
    
