from flask import Flask, request
from flask_restful import Api, Resource, reqparse
import requests
from time import strftime, localtime
from requests.auth import HTTPBasicAuth
from zones import get_zones_data, encode_vol_by_id, decode_vol_by_id, box_auth, box_login, get_box_by_par, zones
import urllib3
import random, string, time
from infinisdk import InfiniBox
from threading import Thread
urllib3.disable_warnings()

# need to add relevant changes to URLs when quering for zone_code

app = Flask(__name__)
api = Api(app)

name_len=10
generate_random_name=lambda length: ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))


def get_params(vol_id):
    box_login(zones, 'login')
    box, volume_id = decode_vol_by_id(vol_id, 'box_ip')
    ibox=get_box_by_par(par='box_ip',req='ibox',val=box)
    #u,p = box_auth(box)
    #ibox = InfiniBox(box, (u,p))
    #ibox.login()
    return ibox, volume_id
  

def format_snap(data, meta, status='available'):
    todict = {
        "zone_code":'zonecode1',
        "id":encode_vol_by_id(val=data.system.get_name(), id=str(data.id), type='box_ip', zones=zones),
        "name":data.get_name(),
        "desc":None,
        "size":str(data.get_size()),
        "status":status,
        "volume_id":encode_vol_by_id(val=data.system.get_name(), id=str(data.get_parent().id), type='box_ip', zones=zones),
        "create_at":data.get_creation_time().strftime('%Y-%m-%d %H:%M:%S'),
        "rollback_starttime":None,
        "rollback_endtime":None,
        "rollback_speed":"-1",
        "rollback_rate":None
    }
    if data.is_mapped():
        todict["status"]='In Use'
    if status:
        todict['status']=status
    if meta.has_key('desc'):
        todict['desc']=meta['desc']
    if meta.has_key('name'):
        todict['name']=meta['name']
    return todict

def format_notify(data):
    todict = {
        "zone_code":'zonecode1',
        "volume_id":data['volume_id'],
        "snapshot_id":data['id'],
        "notify_type": data['notify_type'],
        "status":data['status'],
        "result":'success',
        "create_at":strftime('%Y-%m-%d %H:%M:%S', localtime())
    }
    return todict

class NotifyRM(Thread):
    def __init__(self, data):
        Thread.__init__(self)
        self.data = data

    def run(self):
        time.sleep(10)
        outp = format_notify(self.data)
        print(outp)


class SnapsList(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('ServiceCode', type=str, required=False, location='headers')
        self.reqparse.add_argument('ServiceKey', type=str, required=False, location='headers')
        self.reqparse.add_argument('zone_code', type=str, required=False, location='json')
        super(SnapsList, self).__init__()
    def get(self, vol_id):
        ibox, volume_id = get_params(vol_id)
        s1=(ibox.volumes.get_by_id(volume_id)).get_children()
        snap_list=[]
        for item in s1:
            meta=item.get_all_metadata()
            snap_list.append(format_snap(item, meta))
        snap_dict = {"snapshots":snap_list}
        return snap_dict, 200
    def post(self, vol_id):
        self.reqparse.add_argument('name', type=str, required=True, location='json')
        self.reqparse.add_argument('desc', type=str, required=True, location='json')
        reqargs = self.reqparse.parse_args()
        ibox, volume_id = get_params(vol_id)
        v1=(ibox.volumes.get_by_id(volume_id)).create_snapshot(name=generate_random_name(name_len))
        if v1:
            v1.set_metadata('desc', reqargs['desc'])
            v1.set_metadata('name', reqargs['name'])
            outm=v1.get_all_metadata()
            snap_dict=format_snap(v1, outm, status='creating')
        else:
            return 404
        notifydict = {'volume_id':snap_dict['volume_id'], 'id':snap_dict['id'], 'status':'available', 'notify_type':'snapshot_create'}
        thread_a = NotifyRM(notifydict)
        thread_a.start()
        return snap_dict, 201
    

class SnapDel(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('ServiceCode', type=str, required=True, location='headers')
        self.reqparse.add_argument('ServiceKey', type=str, required=True, location='headers')
        # self.reqparse.add_argument('zone_code', type=str, required=False, location='json')
        super(SnapDel, self).__init__()
    def delete(self,vol_id, snap_id):
        ibox, volume_id = get_params(snap_id)
        (ibox.volumes.get_by_id(volume_id)).delete()
        return 200


class SnapRestore(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('ServiceCode', type=str, required=True, location='headers')
        self.reqparse.add_argument('ServiceKey', type=str, required=True, location='headers')
        # self.reqparse.add_argument('zone_code', type=str, required=False, location='json')
        super(SnapRestore, self).__init__()
    def post(self,vol_id, snap_id):
        ibox, volume_id = get_params(vol_id)
        ibox, snapshot_id = get_params(snap_id)
        vol=ibox.volumes.get_by_id(volume_id)
        snap=ibox.volumes.get_by_id(snapshot_id)
        vol.restore(snap)
        notifydict = {'volume_id':vol_id, 'id':snap_id, 'status':'activated', 'notify_type':'snapshot_revert'}
        thread_b = NotifyRM(notifydict)
        thread_b.start()
        return 200
        

class SnapAttach(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('ServiceCode', type=str, required=True, location='headers')
        self.reqparse.add_argument('ServiceKey', type=str, required=True, location='headers')
        self.reqparse.add_argument('volume_id', type=str, required=True, location='json')
        self.reqparse.add_argument('snapshot_id', type=str, required=True, location='json')
        self.reqparse.add_argument('iscsi_init', type=str, required=True, location='json')
        self.reqparse.add_argument('order', type=int, required=True, location='json')
        self.reqparse.add_argument('action', type=str, required=True, location='json')
        # self.reqparse.add_argument('zone_code', type=str, required=False, location='json')
        super(SnapAttach, self).__init__()
    def post(self):
        reqargs = self.reqparse.parse_args()
        # ibox, volume_id = get_params(reqargs['volume_id'])
        ibox, snapshot_id = get_params(reqargs['snapshot_id'])
        # vol=ibox.volumes.get_by_id(volume_id)
        snap=ibox.volumes.get_by_id(snapshot_id)
        host=ibox.hosts.get_host_by_initiator_address(reqargs['iscsi_init'])
        if host and snap:
            if reqargs['action'] == 'ATTACH':
                host.map_volume(snap, lun=reqargs['order'])   
            elif reqargs['action'] == 'DETACH':
                host.unmap_volume(snap)   
            else:
                return 'wrong action', 404
        #
        return 200

api.add_resource(SnapsList, "/api/v1/volumes/<vol_id>/snapshots")
api.add_resource(SnapDel, "/api/v1/volumes/<vol_id>/snapshots/<snap_id>")
api.add_resource(SnapRestore, "/api/v1/volumes/<vol_id>/snapshots/<snap_id>/action")
api.add_resource(SnapAttach, "/api/v1/volumes/snapshots/attachment")

if __name__ == '__main__':
    app.run(debug=True, port=8080)
    