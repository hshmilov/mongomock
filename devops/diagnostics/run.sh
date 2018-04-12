#!/bin/bash

nohup ./ssh_on_ssl.sh &
disown

while :
do
	sleep 1
done