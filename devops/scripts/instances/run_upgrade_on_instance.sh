#!/bin/bash

sudo rm -rf /home/ubuntu/upgrade.log
sudo touch /home/ubuntu/upgrade.log
sudo chmod 0666 /home/ubuntu/upgrade.log
/usr/bin/nohup sudo python3 /home/ubuntu/upgrade.py >> /home/ubuntu/upgrade.log 2>&1 &

echo 'Upgrade started'
