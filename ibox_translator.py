from flask import Flask, request,abort,jsonify
from flask_restful import Api, Resource, reqparse
from volume import *
from glance import *
from zone import *
from snapshot import *
import logging
logging.basicConfig(filename='ibox_translator.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s')
zone_file='./zones.json'
if __name__ == "__main__":
	global zoneset
	zoneset=get_zones_data(zone_file)
	zoneset=set_box_hexa(zoneset)

#	try:
#		box_login(zoneset)
#	except Exception as E:
#		logging.error("unable to login to infinibox, aborting {}".format(E))
#		exit(5)

	app = Flask(__name__)
	api = Api(app)
	api.add_resource(VolumesList, "/api/v1/volumes")
	api.add_resource(VolumesAttachment, "/api/v1/volumes/attachment")
	api.add_resource(Volume, "/api/v1/volumes/<string:vol_id>")
	api.add_resource(VolumeExpand, "/api/v1/volumes/<string:vol_id>/expand")
	api.add_resource(ImagesList, "/api/v1/images")
	api.add_resource(Image, "/api/v1/images/<reqid>")
	api.add_resource(SnapsList, "/api/v1/volumes/<vol_id>/snapshots")
	api.add_resource(SnapDel, "/api/v1/volumes/<vol_id>/snapshots/<snap_id>")
	api.add_resource(SnapRestore, "/api/v1/volumes/<vol_id>/snapshots/<snap_id>/action")
	api.add_resource(SnapAttach, "/api/v1/volumes/snapshots/attachment")	
	app.run(debug=True, port=8080, host='0.0.0.0')
