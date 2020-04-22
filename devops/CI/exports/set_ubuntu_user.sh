#!/usr/bin/env bash

set -e

sed -i '/PasswordAuthentication/ d' /etc/ssh/sshd_config
sed -i -e '$a\' /etc/ssh/sshd_config
echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config

# adding ubuntu user
if [ $(cat /etc/passwd | grep ubuntu | wc -l) -ne 0 ]; then
    echo "User ubuntu exists or doesn't need to be"
else
    echo "Setting ubuntu user"
    useradd ubuntu
    mkdir -p /home/ubuntu
    chown ubuntu:ubuntu /home/ubuntu
    /usr/sbin/usermod -s /bin/bash ubuntu
    /usr/sbin/usermod -aG wheel ubuntu
fi

echo ubuntu:bringorder | /usr/sbin/chpasswd


echo "ubuntu ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/90-ubuntu

service sshd restart

