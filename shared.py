from threading import Thread
import string, random
from time import strftime, localtime, sleep
import requests

generate_random_name=lambda length: ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))

uri="syncpc/storage-resp.do"
rm_srv="221.148.108.21"
port=8050


def format_notify(data):
    todict = {
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
        sleep(15)
        outp = format_notify(self.data)
        pheaders = {'content-type': "application/json"}
        requests.post(url='http://{}:{}/{}'.format(rm_srv,port,uri), auth=('admin', '123456'), headers=pheaders, json=outp) 
        outp = format_notify(self.data)
        print(outp)