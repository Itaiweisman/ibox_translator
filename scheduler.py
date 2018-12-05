from flask import Flask, request
from flask_restful import Api, Resource, reqparse
from snapshot import *
from shared import generate_random_name
from zone import get_zones_data, encode_vol_by_id, decode_vol_by_id, box_auth, box_login, get_box_by_par, zones
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
schedule_app = Flask(__name__)


# initialize scheduler with your preferred timezone
scheduler = BackgroundScheduler({'apscheduler.timezone': 'UTC'})
# add a custom jobstore to persist jobs across sessions (default is in-memory)
scheduler.add_jobstore('sqlalchemy', url='sqlite:////tmp/schedule.db')
scheduler.start()

def format_sched(job):
    todict = {
        "volume_id":job.id,
        "id":job.id,
        "mon":False,
        "tue":False,
        "wed":False,
        "thu":False,
        "fri":False,
        "sat":False,
        "sun":False,
        "hour":job.args[0]['hrs'],
        "minute":job.args[0]['min'],
        "name":job.name,
        "desc":job.args[0]['desc'],
        "period_of_keep":job.args[0]['period_of_keep'],
        "number_of_keep":job.args[0]['number_of_keep'],
        "status":job.args[0]['status']
        }
    for day in job.args[0]['dow']:
        if day in todict.keys():
            todict[day] = True
    return todict


def take_snap(xtrargs):
    ibox, volume_id = get_params(xtrargs['vol_id'])
    snap_name="autosnap_{}".format(generate_random_name(name_len))
    vol=ibox.volumes.get_by_id(volume_id)
    vol.create_snapshot(name=snap_name)
    snaps=vol.get_children()
    if (xtrargs['number_of_keep'] > 0 and not None) and (len(snaps) > xtrargs['number_of_keep']):
        for i in range(len(snaps) - xtrargs['number_of_keep']):
            if snaps[i].is_mapped():
                continue
            snaps[i].delete()

def delete_snap(xtrargs):
    ibox, volume_id = get_params(xtrargs['vol_id'])
    snaps=(ibox.volumes.get_by_id(volume_id)).get_children()
    for snap in snaps:
        if (snap.get_created_at().now() - snap.get_created_at()).days > xtrargs['period_of_keep']:
            snap.delete()


class ScheduleList(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('ServiceCode', type=str, required=True, location='headers')
        self.reqparse.add_argument('ServiceKey', type=str, required=True, location='headers')
        super(ScheduleList, self).__init__()
    def get(self, vol_id):
        job=scheduler.get_job(vol_id)
	if job:
	        fjob = {"schedule":format_sched(job)}
	        return fjob, 200
	else:
		return 'Not Found', 404
    def post(self, vol_id):
        data=request.get_json()
        dow_lst = [k for k,v in data['schedule'].items() if v == True and type(v) == bool]
        dow = ','.join(dow_lst)
        hrs = data['schedule']['hour']
        mins = data['schedule']['minute']
        if data['schedule']['name']:
            name = data['schedule']['name']
        else:
            name = generate_random_name(name_len)
        sched_id = vol_id
        xtrargs = {'status':data['schedule']['status'],'vol_id':vol_id, 'period_of_keep':data['schedule']['period_of_keep'], 'number_of_keep':data['schedule']['number_of_keep'], 'desc':data['schedule']['desc'], 'dow':dow_lst, 'hrs':data['schedule']['hour'], 'min':data['schedule']['minute'] }
        try:
            job=scheduler.add_job(take_snap, id=sched_id, trigger='cron',name=name, day_of_week=dow, hour=hrs, minute=mins, args=[xtrargs] )
        except Exception as E:
            return "Sorry, {}".format(E[0]), 404
        job2=scheduler.add_job(delete_snap, id="{}-1".format(sched_id), trigger='cron', hour=0, minute=0, args=[xtrargs] )
        if data['schedule']['period_of_keep'] == 0 or None:
            job2.pause()
        if 'disable' in data['schedule']['status']:
            job.pause()
            job2.pause()
        fjob = {"schedule":format_sched(job)}
        return fjob, 201 
   

class Schedule(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('ServiceCode', type=str, required=True, location='headers')
        self.reqparse.add_argument('ServiceKey', type=str, required=True, location='headers')
        super(Schedule, self).__init__()
    def put(self, vol_id, schedule_id):
        data=request.get_json()
        dow_lst = [k for k,v in data['schedule'].items() if v == True and type(v) == bool]
        dow = ','.join(dow_lst)
        hrs = data['schedule']['hour']
        mins = data['schedule']['minute']
        if data['schedule']['name']:
            name = data['schedule']['name']
        xtrargs = {"status":data['schedule']['status'],"vol_id":vol_id, "period_of_keep":data['schedule']['period_of_keep'], "number_of_keep":data['schedule']['number_of_keep'], "desc":data['schedule']['desc'], 'dow':dow_lst, 'hrs':data['schedule']['hour'], 'min':data['schedule']['minute'] }
        sched_id = vol_id
        job=scheduler.get_job(schedule_id)
        job2=scheduler.get_job("{}-1".format(schedule_id))
        job.remove()
        job2.remove()
        try:
            job=scheduler.add_job(take_snap, id=sched_id, trigger='cron',name=name, day_of_week=dow, hour=hrs, minute=mins, args=[xtrargs] )
        except Exception as E:
            return "Sorry, {}".format(E[0]), 404
        job2=scheduler.add_job(delete_snap, id="{}-1".format(sched_id), trigger='cron', hour=0, minute=0, args=[xtrargs] )
        if data['schedule']['period_of_keep'] == 0 or None:
            job2.pause()
        if 'disable' in data['schedule']['status']:
            job.pause()
            job2.pause()
        fjob = {"schedule":format_sched(job)}
        return fjob, 200
    def delete(self, vol_id, schedule_id):
        job=scheduler.get_job(schedule_id)
        job2=scheduler.get_job("{}-1".format(schedule_id))
        if job:
            job.remove()
            job2.remove()
            return  200
        else:
            return "Not Found", 404
        
        


#api.add_resource(ScheduleList, "/api/v1/volumes/<vol_id>/snapshots/schedule")
#api.add_resource(Schedule, "/api/v1/volumes/<vol_id>/snapshots/schedule/<schedule_id>")
#
#if __name__ == '__main__':
#    app.run(debug=True, port=8080)
    
