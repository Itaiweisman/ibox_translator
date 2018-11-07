import json
from infinisdk import InfiniBox
import pprint
pp = pprint.PrettyPrinter(depth=6)
global zones 
id_str="546c4f25-FFFF-FFFF-BBBB-34306c"
box_serial_len=4
volume_id_len=5


def get_zones_data (zone_file):
    f=open(zone_file, 'r')
    zones_data=json.load(f)
    return zones_data

def set_box_hexa(zones):
	for zone in zones['zones']:
		zone['serial_hexa']=hex(zone['serial_dec'])
		

def get_box_by_par(**kwargs):
    for zone in zones['zones']:
        if zone[kwargs['par']] == kwargs['val']:
            return zone[kwargs['req']]


def box_login(zones):
 	for zone in zones['zones']:
 		try:
 			ibox=InfiniBox(zone['box_ip'],(zone['box_user'],zone['box_password']))
 			ibox.login()
 			print ibox.get_name()
 			zone['ibox']=ibox
 		except Exception as E:
 			zone['ibox']=repr(E)

def fix_str(str,req_len):
	embedding_zeros=req_len-len(str)
	new_str=embedding_zeros*'0'+str
	return new_str

def encode_vol_by_id(**kwargs):
	pref=id_str[0:19]
	post=id_str[23:31]
	box=kwargs['val']
	vol=kwargs['id']
	req_type=kwargs['type']
	box_hexa=get_box_by_par(par=req_type,req='serial_hexa',val=box)
	box_hexa=fix_str(box_hexa.replace('0x',''),box_serial_len)
	vol=fix_str(vol,volume_id_len)
	vol_id=pref+box_hexa+post+vol
	return vol_id

def decode_vol_by_id(vol,vtype):
	box='0x'+vol[19:23].replace('0','')
	vol_id=int(vol[-5:])
	box_val=get_box_by_par(par='serial_hexa',req=vtype,val=box)
	#print "box is {} volune is {}".format(box_val,vol_id)
	return box_val, vol_id
zones=get_zones_data('zones.json')
set_box_hexa(zones)

get_box_by_par(par='name',req='box_ip',val='zoneA')
#box_login(zones)



######################

encoded=encode_vol_by_id(val='ibox1499',id='110',type='box_ip')
print "encoded is {}".format(encoded)
box,decoded=decode_vol_by_id('546c4f25-FFFF-FFFF-05db-34306c00110','box_ip')
print "decoded box is {} and volume is {}".format(box,decoded)



### OUTPUT
#encoded is 546c4f25-FFFF-FFFF-05db-34306c00110
#decoded box is ibox1499 and volume is 110