from flask import Flask, request
from flask_restful import Api, Resource, reqparse
from volume import check_iqn_logged_in
# from shared import generate_random_name
from zone import get_zones_data, encode_vol_by_id, decode_vol_by_id, box_auth, box_login, get_box_by_par, zones
from snapshot import get_params
#schedule_app = Flask(__name__)


#app = Flask(__name__)
#api = Api(app)

#def check_iqn_logged_in(system,iqn):
#    initators=system.initiators.to_list()
#    for init in initators:
#        if init.get_address() == iqn:
#            return True
#    return False


def get_iqn(zone):
    ilist=[]
    ibox=get_box_by_par(par='name', req='ibox', val=zone, zones=zones)
    nspaces=ibox.network_spaces.find(service='iSCSI_SERVICE').to_list()
    for ns in nspaces:
        ilist.append({'target':ns.get_field('properties')['iscsi_iqn']})
    return ilist


class GetTraget(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('ServiceCode', type=str, required=True, location='headers')
        self.reqparse.add_argument('ServiceKey', type=str, required=True, location='headers')
        # self.reqparse.add_argument('zone_code', type=str, required=False, location='json')
        super(GetTraget, self).__init__()
    def get(self):
        reqargs = self.reqparse.parse_args()
        iqnlist = []
        if 'zone_code' in request.args:
            iqn=get_iqn(request.args['zone_code'])
            return {"init-target":iqn}
        else:
            for zone in zones['zones']:
                iqnlist.append(get_iqn(zone['name']))
            return {"init-target":iqnlist}


class GetInit(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('ServiceCode', type=str, required=True, location='headers')
        self.reqparse.add_argument('ServiceKey', type=str, required=True, location='headers')
        super(GetInit, self).__init__()
    def get(self, iscsi_init):
        reqargs = self.reqparse.parse_args()
        if 'zone_code' in request.args:
            ibox=ibox=get_box_by_par(par='name', req='ibox', val=request.args['zone_code'], zones=zones)
            if ibox.hosts.get_host_by_initiator_address(iscsi_init):
        	    if not check_iqn_logged_in(ibox, iscsi_init):
        	        return {'iscsi': {"zone_code": request.args['zone_code'], "iscsi_init":iscsi_init, "initiator_status":"online"}}
        	    else:
        	        return {'iscsi': {"zone_code": request.args['zone_code'], "iscsi_init":iscsi_init, "initiator_status":"offline"}}
        else:
		return	{'error':'must specify zone_code'}, 404
	#else:
        #        return {'iscsi': {"zone_code": request.args['zone_code'], "iscsi_init":iscsi_init, "initiator_status":"not-exist"}}


class PCPower(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('ServiceCode', type=str, required=True, location='headers')
        self.reqparse.add_argument('ServiceKey', type=str, required=True, location='headers')
        self.reqparse.add_argument('zone_code', type=str, required=False, location='json')
        self.reqparse.add_argument('iscsi_init', type=str, required=False, location='json')
        super(PCPower, self).__init__()
    def post(self):
        reqargs = self.reqparse.parse_args()
	body = request.json
        ibox=ibox=get_box_by_par(par='name', req='ibox', val=reqargs['zone_code'], zones=zones)
	#vols = (v['volume_id'] for v in body['volumes'])
	vols = [y for x in [v.values() for v in body['volumes']] for y in x]
        if ibox.hosts.get_host_by_initiator_address(reqargs['iscsi_init']):
            if check_iqn_logged_in(ibox, reqargs['iscsi_init']):
		for vol in vols:
			ibox, v = get_params(vol)	
			v1 = ibox.volumes.get_by_id(v)
			v1.set_metadata('status', 'in-use')
                return {'iscsi': {"zone_code": reqargs['zone_code'], "iscsi_init":reqargs['iscsi_init'], "initiator_status":"online"}}
            else:
                return {'iscsi': {"zone_code": reqargs['zone_code'], "iscsi_init":reqargs['iscsi_init'], "initiator_status":"offline"}}
        else:
                return {'iscsi': {"zone_code": reqargs['zone_code'], "iscsi_init":reqargs['iscsi_init'], "initiator_status":"not-available"}}



box_login(zones, 'login')
#api.add_resource(GetTraget, "/api/v1/init-target")
#api.add_resource(GetInit, "/api/v1/iscsi_init/<iscsi_init>")
#api.add_resource(PCPower, "/api/v1/pc_power")
#
#if __name__ == '__main__':
#    app.run(debug=True, port=8080)
    
