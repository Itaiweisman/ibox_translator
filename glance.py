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
            reqargs = self.reqparse.parse_args()
            headers = {'X-Auth-Token': reqargs['ServiceKey']}
            outp = requests.get(url=url,headers=headers)
            if 'name' in request.args:
                imagelist = [image for image in outp.json()['images'] if request.args['name'] in image['name']]
                if imagelist:
                    image_list=[]
                    for item in imagelist:
                            image_list.append(format_image(item))
                    image_dict = {"images":image_list}
                    return image_dict, 200
                else:
                    return 'Not Found', 404
            if outp.status_code == 200:
                image_list=[]
                for item in outp.json()['images']:
                    image_list.append(format_image(item))
                image_dict = {"images":image_list}
                return image_dict, 200
            else:
                return outp.reason, outp.status_code
        else:
            image_list=[]
            for zone in zones['zones']:
                openstack=get_box_by_par(par='name', val=zone['name'], req='openstack_glance',zones=zones)
                url="http://{}:{}/v2/images".format(openstack, glanceport)
                reqargs = self.reqparse.parse_args()
                headers = {'X-Auth-Token': reqargs['ServiceKey']}
                try:
                    outp = requests.get(url=url,headers=headers)
                except Exception as E:
                    print(E.message)
                    exit(1)
		if outp.status_code == 200:
	                for image in outp.json()['images']:
        	            image_list.append(format_image(image))
		else:
			return outp.reason, outp.status_code
            if 'name' in request.args:
                imagelist = [image for image in image_list if request.args['name'] in image['name']]
                if imagelist:
                    image_list=[]
                    for item in imagelist:
                            image_list.append(item)
                    image_dict = {"images":image_list}
                    return image_dict, 200
                else:
                    return 'Not Found', 404
            image_dict = {"images":image_list}
            return image_dict, 200
    


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
    
