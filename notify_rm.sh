#! /bin/sh
DATA=$1
URI="syncpc/storage-resp.do"
SERVER="221.148.108.21"
CURL="/usr/bin/curl"
PORT=8050
SLEEP=15
LOGDIR="/tmp"
LOGNAME="notify.log"
LOG="${LOGDIR}/${LOGNAME}"
if [ ! -f $DATA ] 
then
	date >> ${LOG}
	echo "Cant find ${DATA}"
	exit
fi
sleep $SLEEP
CURL_CMD="$CURL http://${SERVER}:${PORT}/${URI} -u admin:123456 -X POST -H \"Content-Type: application/json\" --data \"@$DATA\" "
echo $CURL_CMD
date >> ${LOG} 2>&1
eval $CURL_CMD >> ${LOG}
rm ${DATA}
