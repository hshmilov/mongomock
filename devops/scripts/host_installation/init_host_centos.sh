#!/usr/bin/env bash

set -o xtrace

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

function _wait_for_yum {
    i=0

    until /usr/bin/yum "$@"
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

function fail {
  echo $1 >&2
  exit 1
}

function retry {
  local n=1
  local max=5
  local delay=5
  while true; do
    "$@" && break || {
      if [[ $n -lt $max ]]; then
        ((n++))
        echo "Command failed. Attempt $n/$max:"
        sleep $delay;
      else
        fail "The command has failed after $n attempts."
      fi
    }
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
echo "CONTAINERIZED: $CONTAINERIZED"
echo ""

sed -i '/PasswordAuthentication/ d' /etc/ssh/sshd_config
sed -i -e '$a\' /etc/ssh/sshd_config
echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config

if [ $(cat /etc/environment | grep LC_ALL | wc -l) -ne 0 ]; then
    echo "Locale settings exist"
else
    echo export LC_ALL=\"en_US.UTF-8\" >> /etc/environment
    echo export LC_CTYPE=\"en_US.UTF-8\" >> /etc/environment
fi

export LC_ALL="en_US.UTF-8"
export LC_CTYPE="en_US.UTF-8"


#echo "Updating the sources..."
#if [ -e /etc/apt/sources.list.d/webupd8team-ubuntu-java-xenial.list ]; then
#    mv /etc/apt/sources.list.d/webupd8team-ubuntu-java-xenial.list /tmp
#fi
#if [ -e /var/lib/dpkg/info/oracle-java8-installer.postinst ]; then
#    mv /var/lib/dpkg/info/oracle-java8-installer.postinst /tmp
#fi
#sed -i "s/deb cdrom.*//g" /etc/apt/sources.list    # remove cdrom sources; otherwise _wait_for_apt update fails
#export DEBIAN_FRONTEND=noninteractive
#dpkg --add-architecture i386

_wait_for_yum -y update
echo "Upgrading..."
_wait_for_yum upgrade -yq
echo "Upgrading Kernel..."
_wait_for_yum install -y epel-release
_wait_for_yum install -y wget yum-utils device-mapper-persistent-data lvm2 sshpass open-vm-tools stunnel htop moreutils gparted sysstat net-tools tmux nano vim curl make gcc git traceroute libffi-devel libxml2-devel libxslt-devel libcurl-devel psmisc
_wait_for_yum groupinstall -y development
_wait_for_yum install -y https://centos7.iuscommunity.org/ius-release.rpm
_wait_for_yum install -y python36 python-pip python-devel python3-devel


echo "Setting python3.6 as the default python and upgrading pip..."
ln -sf /usr/bin/python2 /usr/local/bin/python
ln -sf /usr/bin/python3.6 /usr/local/bin/python3
cp ./uploads/pip.conf /etc/pip.conf
python2 -m pip install --upgrade pip
pip2 install --upgrade wheel
python3 -m pip install --upgrade pip
echo "Installing virtualenv and setuptools..."
pip2 install virtualenv
python3 -m pip install virtualenv
pip2 install --upgrade setuptools
python3 -m pip install --upgrade setuptools
python3 -m pip install ipython urllib3 requests
python3 -m pip install netifaces==0.10.9
python3 -m pip install python-crontab==2.4.0
pip2 install distro==1.4.0

echo "Done upgrading"


#_wait_for_apt install -yq apt-transport-https ca-certificates curl software-properties-common # required for https-repos
#curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -
#retry timeout 20 add-apt-repository \
#   "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
#   $(lsb_release -cs) \
#   stable"

echo "Installing various dependencies..."
#_wait_for_apt install -yq moreutils gparted sysstat net-tools iputils-ping libpq-dev tmux screen nano vim curl libffi-dev libxml2-dev libxslt-dev musl-dev make gcc tcl-dev tk-dev git libpango1.0-0 libcairo2 software-properties-common ssh libxmlsec1 ncdu traceroute libc6:i386 libstdc++6:i386
echo "Installing docker-ce..."
yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
mkdir -p /etc/docker
_wait_for_yum install -y docker-ce
systemctl start docker
systemctl enable docker
echo "Adding ubuntu to the docker group, please note that you must logout and login!"
usermod -aG docker $USER
usermod -aG docker ubuntu
echo "Installing weave"
cd "$(dirname "$0")"
cp ./uploads/weave-2.7.0 /usr/local/bin/weave
chmod a+x /usr/local/bin/weave

# Timezone settings should be set on the host of containerized systems (It automatically sets the container clock as well).
echo "Setting system-wide settings and htp"
curl http://rpmfind.net/linux/dag/redhat/el7/en/x86_64/dag/RPMS/htpdate-1.1.0-1.el7.rf.x86_64.rpm -o htpdate-1.1.0-1.el7.rf.x86_64.rpm
rpm -Uvh htpdate-1.1.0-1.el7.rf.x86_64.rpm
yum install -y htpdate
systemctl enable htpdate
rm -f htpdate-1.1.0-1.el7.rf.x86_64.rpm
timedatectl set-timezone UTC

if [ $(cat /etc/passwd | grep netconfig | wc -l) -ne 0 ]; then
    echo "User netconfig exists or doesn't need to be"
else
    echo "Setting netconfig user"
    useradd netconfig
    mkdir -p /home/netconfig
    chown netconfig /home/netconfig
    usermod -s /home/netconfig/login netconfig
    echo netconfig:netconfig | /usr/sbin/chpasswd
    cp ./uploads/ip_wizard/login.c /home/netconfig/login.c
    cp ./uploads/ip_wizard/login.py /home/netconfig/login.py
    cd /home/netconfig
    gcc login.c -o login && chown root:root /home/netconfig/login && chmod 4555 /home/netconfig/login
    chown root:root /home/netconfig/login.py
    chmod 0444 /home/netconfig/login.py
    echo DenyUsers netconfig >> /etc/ssh/sshd_config
    service sshd restart
    echo "Done setting user netconfig"
fi

# adding customer user
if [ $(cat /etc/passwd | grep customer | wc -l) -ne 0 ]; then
    echo "User customer exists or doesn't need to be"
else
    echo "Setting customer user"
    useradd customer
    mkdir -p /home/customer
    chown customer:customer /home/customer
    /usr/sbin/usermod -s /bin/bash customer
    /usr/sbin/usermod -aG wheel customer
    echo customer:customer | /usr/sbin/chpasswd
fi


DECRYPT_USER=decrypt
if [ $(cat /etc/passwd | grep $DECRYPT_USER | wc -l) -ne 0 ]; then
    echo "User $DECRYPT_USER exists"
else
    cd $SCRIPT_DIR
    echo "Setting $DECRYPT_USER user"
    useradd $DECRYPT_USER
    mkdir -p /home/$DECRYPT_USER
    chown decrypt /home/$DECRYPT_USER
    usermod -s /home/$DECRYPT_USER/decrypt_user.py decrypt
    usermod -aG wheel $DECRYPT_USER
    echo $DECRYPT_USER:decrypt | /usr/sbin/chpasswd
    cp ./uploads/decrypt_wizard/decrypt_user.py /home/$DECRYPT_USER/decrypt_user.py
    cp ./uploads/decrypt_wizard/first_install.py /home/$DECRYPT_USER/first_install.py
    cp ./uploads/decrypt_wizard/install_and_run.sh /home/$DECRYPT_USER/install_and_run.sh
    chmod +x /home/$DECRYPT_USER/install_and_run.sh
    chown -R $DECRYPT_USER:$DECRYPT_USER /home/$DECRYPT_USER/
    chmod 0744 /home/$DECRYPT_USER/*.py
    echo "decrypt ALL=(ALL) NOPASSWD: /home/$DECRYPT_USER/first_install.py" > /etc/sudoers.d/90-decrypt
    echo "Done setting user $DECRYPT_USER"
fi

echo "making ubuntu passwordless sudo"
echo "ubuntu ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/90-ubuntu

echo "Installing swap"
# On containerized system the swap should be configured on the host.
if [ $(cat /etc/fstab | grep swapfile | wc -l) -ne 0 ]; then
    echo "Swap file exists"
else
    if [[ $* == *--no-swap* ]]; then
        echo "--no-swap was requested, not allocating swap"
    else
        dd if=/dev/zero of=/swapfile count=16384 bs=1MiB status=progress
        dd if=/dev/zero count=16384 bs=1MiB status=progress >> /swapfile
        dd if=/dev/zero count=16384 bs=1MiB status=progress >> /swapfile
        dd if=/dev/zero count=16384 bs=1MiB status=progress >> /swapfile
        chmod 600 /swapfile
        mkswap /swapfile
        swapon /swapfile
        echo /swapfile swap swap defaults 0 0 >> /etc/fstab
        echo "Done installing swap file, free -h:"
        free -h
    fi
fi

echo "Set pid max"
if [ $(cat /etc/sysctl.conf | grep 'kernel.pid_max' | wc -l) -ne 0 ]; then
    sed -i 's/^\(kernel\.pid_max\s*=\s*\).*/\164000/' /etc/sysctl.conf
else
    echo "kernel.pid_max = 64000" >> /etc/sysctl.conf
fi

echo "Set thread max"
if [ $(cat /etc/sysctl.conf | grep 'kernel.threads-max' | wc -l) -ne 0 ]; then
    sed -i 's/^\(kernel\.threads-max\s*=\s*\).*/\1200000/' /etc/sysctl.conf
else
    echo "kernel.threads-max = 200000" >> /etc/sysctl.conf
fi

echo "Disable ICMP Redirection"
if [ $(cat /etc/sysctl.conf | grep 'net.ipv4' | wc -l) -ne 0 ]; then
    echo "configuration already exist or doesn't need to be"
else
    echo "net.ipv4.conf.all.accept_redirects = 0" >> /etc/sysctl.conf
    echo "net.ipv4.conf.default.accept_redirects = 0" >> /etc/sysctl.conf
    echo "net.ipv4.conf.all.secure_redirects = 0" >> /etc/sysctl.conf
    echo "net.ipv4.conf.default.secure_redirects = 0" >> /etc/sysctl.conf
fi

sysctl --load


if [[ -d "/etc/scalyr-agent-2" ]] ; then
    echo "scalyr exist or doesn't need to be"
else
    echo "install scalyr agent"
    wget -q https://www.scalyr.com/scalyr-repo/stable/latest/scalyr-repo-bootstrap-1.2.2-1.noarch.rpm
    _wait_for_yum remove scalyr-repo scalyr-repo-bootstrap  # Remove any previous repository definitions, if any.
    _wait_for_yum install -y --nogpgcheck scalyr-repo-bootstrap-1.2.2-1.noarch.rpm
    _wait_for_yum install -y scalyr-repo
    _wait_for_yum install -y scalyr-agent-2
    rm scalyr-repo-bootstrap-1.2.2-1.noarch.rpm
fi

if [[ $(/bin/systemctl is-enabled tmp.mount) == "enabled" ]]; then
    echo "/tmp already configured"
else
    echo "making sure /tmp gets deleted on boot"
    cp /lib/systemd/system/tmp.mount /etc/systemd/system/tmp.mount
    /bin/systemctl unmask tmp.mount
    /bin/systemctl enable tmp.mount
fi


# Set systlog
echo "*.*                                                     /var/log/syslog" >> /etc/rsyslog.conf

# Locking root user to ssh
passwd --lock root

# Install Zscaler root certificate
set +e
sudo cp ./uploads/ZscalerRootCertificate-2048-SHA256.crt /usr/local/share/ca-certificates/
sudo chown root:root /usr/local/share/ca-certificates/ZscalerRootCertificate-2048-SHA256.crt
sudo chmod 0444 /usr/local/share/ca-certificates/ZscalerRootCertificate-2048-SHA256.crt
sudo update-ca-certificates
set -e

touch $INIT_FILE
echo "Done successfully"
