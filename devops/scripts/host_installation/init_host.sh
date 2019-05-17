#!/usr/bin/env bash

function _wait_for_apt {
    i=0

    until /usr/bin/apt-get "$@"
    do
        ((i=i+1))
        if [ $i -gt 20 ]
        then
            echo "Timeout reached on $@!"
            exit 1
        fi
        echo "Waiting $i..."
        sleep 60
    done

}

set -e

# Notice! This image initializes a plain host image to include all the requirements of Axonius.
# It should be run only once, as root, and be non-interactive!
#
# DO NOT CHANGE ME UNLESS YOU KNOW WHAT YOU DO. PLEASE READ THE FOLLOWING
#
# If you intend to add new functionality to the system, it might not work on *upgrade* since this file
# is called only once for new Axonius instances. put upgrade commands somewhere else!


if [[ $UID -ne 0 ]]; then
    echo "this script must run as root!"
    exit 1
fi;
INIT_FILE=/home/ubuntu/.axonius_done_init_host
if [ -e "$INIT_FILE" ]; then
    echo "Initialization was done already! exiting"
    exit 0
fi
echo "Initializing the host image.."
echo "hostname: $(hostname)"
echo ""


echo "Updating the sources..."
if [ -e /etc/apt/sources.list.d/webupd8team-ubuntu-java-xenial.list ]; then
    sudo mv /etc/apt/sources.list.d/webupd8team-ubuntu-java-xenial.list /tmp
fi
if [ -e /var/lib/dpkg/info/oracle-java8-installer.postinst ]; then
    sudo mv /var/lib/dpkg/info/oracle-java8-installer.postinst /tmp
fi
sed -i "s/deb cdrom.*//g" /etc/apt/sources.list    # remove cdrom sources; otherwise _wait_for_apt update fails
export DEBIAN_FRONTEND=noninteractive
sudo dpkg --add-architecture i386
_wait_for_apt update
echo "Upgrading..."
_wait_for_apt upgrade -yq -f
echo "Done upgrading"
_wait_for_apt install -yq apt-transport-https ca-certificates curl software-properties-common # required for https-repos
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
add-apt-repository \
   "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
   $(lsb_release -cs) \
   stable"
add-apt-repository -y ppa:jonathonf/python-3.6
_wait_for_apt update
echo "Installing various dependencies..."
_wait_for_apt install -yq sshpass open-vm-tools stunnel4 htop moreutils gparted sysstat python-apt python3-apt net-tools iputils-ping libpq-dev tmux screen nano vim curl python3-dev python-dev libffi-dev libxml2-dev libxslt-dev musl-dev make gcc tcl-dev tk-dev openssl git python libpango1.0-0 libcairo2 software-properties-common python-software-properties ssh libxmlsec1 ncdu traceroute libc6:i386 libstdc++6:i386
echo "Installing python 3.6..."
_wait_for_apt install -yq python3.6 python3.6-dev python3.6-venv ipython python-pip htpdate
curl https://bootstrap.pypa.io/get-pip.py | python3.6
# The following is a horrible hack we are doing to make python3.6 the default on ubuntu 16.04.
# By default, ubuntu 16.04 does not support python3.6 being the default python because many of its apps are written
# in python3.5 which also uses binary shared-objects. so changing /usr/bin/python3 will result in making the whole
# system unstable but on the other hand /usr/local/bin is still in our path and we can use it.
# so eventually /usr/bin/python3 will point to python3.5 and /usr/local/bin/python3 will point to python3.6.
echo "Setting python3.6 as the default python and upgrading pip..."
ln -sf /usr/bin/python2 /usr/local/bin/python
ln -sf /usr/bin/python3.6 /usr/local/bin/python3
python2 -m pip install --upgrade pip
python3 -m pip install --upgrade pip
echo "Installing virtualenv and setuptools..."
pip2 install virtualenv
pip3 install virtualenv
pip2 install --upgrade setuptools
pip3 install --upgrade setuptools
pip3 install ipython
echo "Installing docker-ce..."
_wait_for_apt install -yq docker-ce=18.06.3~ce~3-0~ubuntu
systemctl enable docker
echo "Adding ubuntu to the docker group, please note that you must logout and login!"
usermod -aG docker ubuntu
gpasswd -a ubuntu docker
echo "Installing weave"
cd "$(dirname "$0")"
cp ./weave-2.5.1 /usr/local/bin/weave
chmod a+x /usr/local/bin/weave
echo "Setting system-wide settings"
sudo timedatectl set-timezone UTC

if [ $(cat /etc/environment | grep LC_ALL | wc -l) -ne 0 ]; then
    echo "Locale settings exist"
else
    echo export LC_ALL=\"en_US.UTF-8\" >> /etc/environment
    echo export LC_CTYPE=\"en_US.UTF-8\" >> /etc/environment
fi

if [ $(cat /etc/passwd | grep netconfig | wc -l) -ne 0 ]; then
    echo "User netconfig exists"
else
    echo "Setting netconfig user"
    useradd netconfig
    mkdir /home/netconfig
    chown netconfig /home/netconfig
    usermod -s /home/netconfig/login netconfig
    echo netconfig:netconfig | /usr/sbin/chpasswd
    cp ./ip_wizard/login.c /home/netconfig/login.c
    cp ./ip_wizard/login.py /home/netconfig/login.py
    cd /home/netconfig
    gcc login.c -o login && chown root:root /home/netconfig/login && chmod 4555 /home/netconfig/login
    chown root:root /home/netconfig/login.py
    chmod 0444 /home/netconfig/login.py
    echo DenyUsers netconfig >> /etc/ssh/sshd_config
    service ssh restart
    echo "Done setting user netconfig"
fi

# adding customer user
if [ $(cat /etc/passwd | grep customer | wc -l) -ne 0 ]; then
    echo "User customer exists"
else
    echo "Setting customer user"
    useradd customer
    mkdir /home/customer
    chown customer:customer /home/customer
    /usr/sbin/usermod -s /bin/bash customer
    /usr/sbin/usermod -aG sudo customer
    echo customer:customer | /usr/sbin/chpasswd
fi

echo "Installing swap"
if [ $(cat /etc/fstab | grep swapfile | wc -l) -ne 0 ]; then
    echo "Swap file exists"
else
    fallocate -l 64G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo /swapfile swap swap defaults 0 0 >> /etc/fstab
    echo "Done installing swap file, free -h:"
    free -h
fi
touch $INIT_FILE
echo "Done successfully"
