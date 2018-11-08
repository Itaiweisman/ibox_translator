from flask import Flask, request,abort,jsonify
from flask_restful import Api, Resource, reqparse
from volume import *
from zone import *
if __name__ == "__main__":
	app = Flask(__name__)
	api = Api(app)
	api.add_resource(VolumesList, "/api/v1/volumes")
	api.add_resource(VolumesAttachment, "/api/v1/volumes/attachment")
	api.add_resource(Volume, "/api/v1/volumes/<string:vol_id>")
	api.add_resource(VolumeExpand, "/api/v1/volumes/<string:vol_id>/expand")
	app.run(debug=True, port=8080, host='0.0.0.0')