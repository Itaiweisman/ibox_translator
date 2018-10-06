#! /bin/sh
DATA=$1
URI="/api/rest/volumes"
SERVER="ibox1499"
CURL="/usr/bin/curl"
PORT=80
SLEEP=5
LOGDIR="/tmp"
LOGNAME="notify.log"
LOG="${LOGDIR}/${LOGNAME}"
sleep $SLEEP
CURL_CMD="$CURL http://${SERVER}:${PORT}/${URI} -u iscsi:123456 -X POST -H \"Content-Type: application/json\" --data \"@$DATA\" "
echo $CURL_CMD
date >> ${LOG} 2>&1
eval $CURL_CMD >> ${LOG}
