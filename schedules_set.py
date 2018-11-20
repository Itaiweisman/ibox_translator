import sqlite3,datetime
import os
from infinisdk import InfiniBox
weekdays = ["MON","TUE","WED","THU","FRI","SAT", "SUN"]
db="/root/snapshots"
at="/usr/bin/at"
sample_snap="/usr/bin/sample_snap"
snap_script='./run_snap.py'
table="schedules"

today=weekdays[datetime.datetime.today().weekday()-1]
def connect_to_db(db):
	try:
		conn = sqlite3.connect(db)
		cursor=conn.cursor()
		return conn,cursor
	except Exception as E:
		print "cannot connect to db",E
		exit(50)


def get_todays_snapshots(cursor,table,today):
	statement="select volume_id, hour,minute from {} where {} = 1 and status = 'runnable' ".format(table,today)
	cursor.execute(statement)
	return cursor.fetchall()

def create_todays_snapshots(vol_id,time,to_keep,box):
	cmd="echo {} {} | {} {}".format(sample_snap, vol_id, at, time)
	cmd=at+' '+time+' '+snap_script+' '+vol_id+' '+to_keep+' '+' '+box
	os.system(cmd)

def delete_old_snaps():
	pass
	

connection,cursor=connect_to_db(db)
todays=get_todays_snapshots(cursor,table,today)
print todays
for snap in todays:
	vol_id,hour,minute=snap
	time=str(hour)+":"+str(minute)
	create_todays_snapshots(vol_id,time)
	
		
