#!/bin/bash

/usr/bin/nohup sudo python3 /home/ubuntu/upgrade.py >> /home/ubuntu/upgrade.log 2>&1 &

echo 'Upgrade started'
