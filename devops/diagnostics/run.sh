#!/bin/bash

nohup ./ssh_on_ssl.sh &
disown

sleep 3

nohup ./ssh_on_443.sh &
disown

while :
do
	sleep 1
done