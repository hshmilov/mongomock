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
systemctl restart sshd

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

_wait_for_apt update
echo "Upgrading..."
_wait_for_apt upgrade -yq -f
echo "Done upgrading"

echo -e "nameserver 10.0.2.68\n$(cat /etc/resolv.conf)" > /etc/resolv.conf
_wait_for_apt install -yq apt-transport-https ca-certificates curl software-properties-common # required for https-repos
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
retry timeout 20 add-apt-repository \
   "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
   $(lsb_release -cs) \
   stable"

cd "$(dirname "$0")"
_wait_for_apt update
echo "Installing various dependencies..."
_wait_for_apt install -yq python3 python3-pip docker-ce  awscli
cp ./daemon.json /etc/docker/daemon.json
pip3 install -U docker pip
systemctl restart docker
usermod -aG docker ubuntu
gpasswd -a ubuntu docker

systemctl enable docker

touch $INIT_FILE
echo "Done successfully"
