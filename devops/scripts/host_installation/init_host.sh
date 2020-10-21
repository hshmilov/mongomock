#!/usr/bin/env bash

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

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
echo ""

echo "127.0.0.1 $(hostname)" >> /etc/hosts
sed -i '/PasswordAuthentication/ d' /etc/ssh/sshd_config
sed -i -e '$a\' /etc/ssh/sshd_config
echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config

# Make sure ssh runs at boot
update-rc.d ssh defaults
systemctl enable ssh.socket
systemctl enable ssh.service

if [ $(cat /etc/environment | grep LC_ALL | wc -l) -ne 0 ]; then
    echo "Locale settings exist"
else
    echo export LC_ALL=\"en_US.UTF-8\" >> /etc/environment
    echo export LC_CTYPE=\"en_US.UTF-8\" >> /etc/environment
fi
export LC_ALL="en_US.UTF-8"
export LC_CTYPE="en_US.UTF-8"

sed -i "s/deb cdrom.*//g" /etc/apt/sources.list    # remove cdrom sources; otherwise _wait_for_apt update fails
export DEBIAN_FRONTEND=noninteractive
echo -e "nameserver 10.0.2.68\n$(cat /etc/resolv.conf)" > /etc/resolv.conf

_wait_for_apt update
_wait_for_apt install -yq apt-transport-https ca-certificates curl software-properties-common open-vm-tools build-essential makeself moreutils socat sshpass nano vim curl traceroute tmux # required for https-repos
echo "Adding docker repo"
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -
retry timeout 20 add-apt-repository \
   "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
   $(lsb_release -cs) \
   stable"

echo "Add python3.6 key and repo"
curl -sSk https://nexus.pub.axonius.com/ppa_certs/deadcert.key | apt-key add -
source /etc/lsb-release
add-apt-repository "deb https://axoniusreadonly:7wr7E6kfttdVgn5e@nexus.pub.axonius.com/repository/proxy-python3.6 $(lsb_release -cs) main"
cd $SCRIPT_DIR
cp ./uploads/nexus-apt /etc/apt/apt.conf.d/nexus


echo "Installing python 3.6..."
_wait_for_apt update
_wait_for_apt install -yq python3.6 python3.6-dev python3.6-venv ipython python-pip htpdate unixodbc-dev
curl -o /tmp/get-pip.py https://bootstrap.pypa.io/get-pip.py
python3.6 /tmp/get-pip.py pip==19.3.1 setuptools==49.6.0
rm -f /tmp/get-ip.py
# The following is a horrible hack we are doing to make python3.6 the default on ubuntu 16.04.
# By default, ubuntu 16.04 does not support python3.6 being the default python because many of its apps are written
# in python3.5 which also uses binary shared-objects. so changing /usr/bin/python3 will result in making the whole
# system unstable but on the other hand /usr/local/bin is still in our path and we can use it.
# so eventually /usr/bin/python3 will point to python3.5 and /usr/local/bin/python3 will point to python3.6.
echo "Setting python3.6 as the default python and upgrading pip..."
ln -sf /usr/bin/python2 /usr/local/bin/python
ln -sf /usr/bin/python3.6 /usr/local/bin/python3
cp ./uploads/pip.conf /etc/pip.conf


echo "Installing docker-ce..."
_wait_for_apt update
_wait_for_apt install -yq docker-ce containerd.io
systemctl enable docker
echo "Adding ubuntu to the docker group, please note that you must logout and login!"
usermod -aG docker ubuntu
gpasswd -a ubuntu docker

cd $SCRIPT_DIR
echo "dir"
echo pwd
echo "What is inside:"
ls -la


echo "Installing weave"
cp ./uploads/weave-2.7.0 /usr/local/bin/weave
echo "Restarting Docker Service for Registry setup"
systemctl restart docker
chmod a+x /usr/local/bin/weave

echo "Setting system-wide settings"
timedatectl set-timezone UTC

if [ $(cat /etc/passwd | grep netconfig | wc -l) -ne 0 ]; then
    echo "User netconfig exists"
else
    echo "Setting netconfig user"
    useradd netconfig
    mkdir /home/netconfig
    chown netconfig /home/netconfig
    usermod -s /home/netconfig/login netconfig
    echo netconfig:netconfig | /usr/sbin/chpasswd
    cp ./uploads/ip_wizard/login.c /home/netconfig/login.c
    cp ./uploads/ip_wizard/login.py /home/netconfig/login.py
    cd /home/netconfig
    gcc login.c -o login && chown root:root /home/netconfig/login && chmod 4555 /home/netconfig/login
    cd $SCRIPT_DIR
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



echo "making ubuntu passwordless sudo"
echo "ubuntu ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/90-ubuntu

echo "Installing swap"
if [ $(cat /etc/fstab | grep swapfile | wc -l) -ne 0 ]; then
    echo "Swap file exists"
else
    if [[ $* == *--no-swap* ]]; then
        echo "--no-swap was requested, not allocating swap"
    else
        fallocate -l 64G /swapfile
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
    echo "configuration already exist"
else
    echo "net.ipv4.conf.all.accept_redirects = 0" >> /etc/sysctl.conf
    echo "net.ipv4.conf.default.accept_redirects = 0" >> /etc/sysctl.conf
    echo "net.ipv4.conf.all.secure_redirects = 0" >> /etc/sysctl.conf
    echo "net.ipv4.conf.default.secure_redirects = 0" >> /etc/sysctl.conf
    if [ $(sysctl -n net.core.somaxconn) -lt 20000 ]; then
      echo "net.core.somaxconn = 20000" >> /etc/sysctl.conf
    else
      echo "net.core.somaxconn status is $(sysctl -n net.core.somaxconn)"
    fi
fi

sysctl --load

if [ $(sysctl -n net.core.somaxconn) -lt 20000 ]; then
  echo "Updated net.core.somaxconn to 20000"
  sysctl -w net.core.somaxconn=20000
fi

if [[ -d "/etc/scalyr-agent-2" ]]; then
    echo "scalyr exist"
else
    echo "install scalyr agent"
    wget -q https://www.scalyr.com/scalyr-repo/stable/latest/scalyr-repo-bootstrap_1.2.2_all.deb
    dpkg -r scalyr-repo scalyr-repo-bootstrap  # Remove any previous repository definitions, if any.
    dpkg -i scalyr-repo-bootstrap_1.2.2_all.deb
    set +e
    _wait_for_apt update
    set -e
    echo "Passing confdef and confold"
    _wait_for_apt -o Dpkg::Options::="--force-confnew" -o Dpkg::Options::="--force-confdef"  install scalyr-repo -y
    _wait_for_apt -o Dpkg::Options::="--force-confold" -o Dpkg::Options::="--force-confdef" install scalyr-agent-2 -y
    rm scalyr-repo-bootstrap_1.2.2_all.deb
fi

#### Go patch TO DELETE after updating builds web####
sudo /bin/bash -c 'echo -e "#!/bin/bash\necho OK;exit 0" > /usr/bin/go'
sudo chmod +x /usr/bin/go

# Install Zscaler root certificate
set +e
cp ./uploads/ZscalerRootCertificate-2048-SHA256.crt /usr/local/share/ca-certificates/
chown root:root /usr/local/share/ca-certificates/ZscalerRootCertificate-2048-SHA256.crt
chmod 0444 /usr/local/share/ca-certificates/ZscalerRootCertificate-2048-SHA256.crt
update-ca-certificates
set -e

touch $INIT_FILE
echo "Done successfully"
