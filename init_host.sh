#!/usr/bin/env bash
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
INIT_FILE=/home/$SUDO_USER/.axonius_done_init_host
if [ -e "$INIT_FILE" ]; then
    echo "Initialization was done already! exiting"
    exit 0
fi
echo "Initializing the host image.."
echo "username: $SUDO_USER"
echo "hostname: $(hostname)"
echo ""
echo "Updating the sources..."
apt-get install -y apt-transport-https ca-certificates curl software-properties-common # required for https-repos
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
add-apt-repository \
   "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
   $(lsb_release -cs) \
   stable"
add-apt-repository -y ppa:jonathonf/python-3.6
sed -i "s/deb cdrom.*//g" /etc/apt/sources.list    # remove cdrom sources; otherwise apt-get update fails
apt-get update
echo "Installing various dependencies..."
apt-get install -y htop sysstat python-apt python3-apt net-tools iputils-ping libpq-dev tmux screen nano vim curl python3-dev python-dev libffi-dev libxml2-dev libxslt-dev musl-dev make gcc tcl-dev tk-dev openssl git python libpango1.0-0 libcairo2 software-properties-common python-software-properties ssh libxmlsec1
echo "Installing python 3.6..."
apt-get install -y python3.6 python3.6-dev python3.6-venv ipython python-pip
curl https://bootstrap.pypa.io/get-pip.py | python3.6
# The following is a horrible hack we are doing to make python3.6 the default on ubuntu 16.04.
# By default, ubuntu 16.04 does not support python3.6 being the default python because many of its apps are written
# in python3.5 which also uses binary shared-objects. so changing /usr/bin/python3 will result in making the whole
# system unstable but on the other hand /usr/local/bin is still in our path and we can use it.
# so eventually /usr/bin/python3 will point to python3.5 and /usr/local/bin/python3 will point to python3.6.
echo "Setting python3.6 as the default python and upgrading pip..."
ln -sf /usr/bin/python3.6 /usr/local/bin/python3
ln -sf /usr/bin/python3.6 /usr/local/bin/python
python2 -m pip install --upgrade pip
python3 -m pip install --upgrade pip
ln -sf /usr/local/bin/pip3 /usr/local/bin/pip
echo "Installing virtualenv and setuptools..."
pip2 install virtualenv
pip3 install virtualenv
pip2 install --upgrade setuptools
pip3 install --upgrade setuptools
echo "Installing docker-ce..."
apt-get install -y docker-ce=18.03.0~ce-0~ubuntu
systemctl enable docker
echo "Adding $SUDO_USER to the docker group, please note that you must logout and login!"
usermod -aG docker $SUDO_USER
echo "Installing weave"
curl -L git.io/weave -o /usr/local/bin/weave
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
    cd "$(dirname "$0")"
    cp devops/scripts/ip_wizard/login.c /home/netconfig/login.c
    cp devops/scripts/ip_wizard/login.py /home/netconfig/login.py
    cd /home/netconfig
    gcc login.c -o login && chown root:root /home/netconfig/login && chmod 4555 /home/netconfig/login
    chown root:root /home/netconfig/login.py
    chmod 0444 /home/netconfig/login.py
    echo DenyUsers netconfig >> /etc/ssh/sshd_config
    service ssh restart
    echo "Done setting user netconfig"
fi
echo "Installing swap"
if [ $(cat /etc/fstab | grep swapfile | wc -l) -ne 0 ]; then
    echo "Swap file exists"
else
    fallocate -l 16G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo /swapfile swap swap defaults 0 0 >> /etc/fstab
    echo "Done installing swap file, free -h:"
    free -h
fi
touch $INIT_FILE
echo "Done successfully"