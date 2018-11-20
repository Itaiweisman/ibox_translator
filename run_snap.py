import sqlite3
import sys
from infinisdk import InfiniBox
import datetime
import time
from zone import *
volume_id=sys.argv[1]
number_to_keep=sys.argv[2]
box=sys.argv[3]
db="/root/snapshots"
table="schedules"
snap_name='SCHED_SNAP'
zone_file='./zones.json'


### Tasks - add logging, add zones and log in
weekdays = ["MON","TUE","WED","THU","FRI","SAT", "SUN"]
today=weekdays[datetime.datetime.today().weekday()-1]
now=datetime.datetime.now()
epoch=time.time()

def connect_to_db(db):
        try:
                conn = sqlite3.connect(db)
                cursor=conn.cursor()
                return conn,cursor
        except Exception as E:
                print "cannot connect to db",E
                exit(50)


def verify_vol_snap_data(cursor,table,today,volume):
	statement="select hour,minute from {} where volume_id={} and status='runnable' ".format(table,volume)
	cursor.execute(statement)
	return cursor.fetchall()

def create_snapshot(volume):
	snapshot_name=snap_name+epoch
	try:
		volume.create_snapshot(name=snapshot_name)
	except Exception as E:
		#Add logging
		pass


def delete_snap(volume,number_to_keep):
	snapshot_list=volume.get_children().to_list()
	count=0
	snap_list=[]
	for snap in snapshot_list:
		if snap.get_name().startswith(snap_name):
			snap_list.append(snap)
	if len(snap_list) > number_to_keep:
		to_delete=number_to_keep-len(snap_list)
		snap_list.reverse()
		while count <= to_delete():
			snap_list[count].delete()
			count=count+1
	
	
conn,cursor=connect_to_db(db)


if name == "__main__":	
	connection,cursor=connect_to_db(db)
	should_run=verify_vol_snap_data(cursor,table,today,volume)
	global zoneset
	zoneset=get_zones_data(zone_file)
	try:
		box_login(zoneset,'login')
		system=get_box_by_par(par='box_ip',req='ibox',val=box)
		volume=system.volumes.find(id=volume_id)
		if volume:
			volume=volume[0]
		else:
			print "can't find volume"
			exit(10)
		
	if should_run:
		hour=should_run[0][0]
		minute=should_run[0][1]
		runtime=now.replace(hour=hour,minute=minute)
	if now >= runtime:
		if create_snapshot(volume):
			print "created snapshot"
			if delete_snap(volume,number_to_keep):
				print "done"
		else:
			print "Failed running"
		#print "should run!"

	else:
	    print "shouldn't run!"

