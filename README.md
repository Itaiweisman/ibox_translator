# INFINIDAT API Translator 
## Written By Itai Weisman, Solution Engineering Team Leader, INFINIDAT; Idan Brenner, Solution Engineer, INFINIDAT

### Change Control
Version | Who	| What | When 
---- | ---- | ---------- | ------------- 
0.1	| Itai Weisman, Idan Brenner | Gensis	| October 18th, 2018 


### About
Due to a INFINIDAT customer request, who currently uses (and wishes to preserve) Huawei OceanStor and StorageOS Multi Service System (SOS) for automation and orchestration of storage management tasks (such as volume provisioning, snapshot management and so on) , we have developed a standalone, 'translator'. 
the 'translator' receives and respectes API requests as defined on the SOS, translate the into InfiniBox API and forward them to an InfiniBox, parse the response sent back from the InfiniBox and send it back to the request initator, while chaging the response format to match the one used by SOS.
with some operations, it is also configured to send back a notification of the response outcome, asynchronously to the requester. 
code is written in python, using infinisdk and flask modules.

### Note
This is a primarely version that covers only the following APIs:

- Volume Provisioning
- Volume Deletion
- Volume Query


for full listing of API request and response please refer to API-Translator DRAFT_GENERAL under the documenation directory

### invocation:

```
python flaskrest.py
```
the notify.sh script is used for notifying back to requester.


