#!/bin/bash
# This script is intended to install Axonius on complex scenarios where our regular deployment image is not working.
# In that case we require the customer to deploy an empty Ubuntu 16.04 machine.
# Make sure you have the latest versions of the links below uploaded to s3.
# Upload this script to a public storage then download and run it.
#
# To pack init_host.tar.gz:
# cd ./devops/scripts/host_installation
# tar -pcvzf init_host.tar.gz .

# wget http://axonius-releases.s3-accelerate.amazonaws.com/deploy_axonius_bash.sh; chmod +x ./deploy_axonius_bash.sh; sudo ./deploy_axonius_bash.sh
set -e
INIT_HOST_TAR_GZ=http://axonius-releases.s3-accelerate.amazonaws.com/init_host.tar.gz
STANDALONE_CHEF_PROVISIONER_URL=http://axonius-releases.s3-accelerate.amazonaws.com/standalone_chef_provisioner.py
AXONIUS_PY_URL=https://s3.us-east-2.amazonaws.com/axonius-releases/latest_release/axonius_upgrader.py

# Color things
cecho () {

    declare -A colors;
    colors=(\
        ['black']='\E[0;47m'\
        ['red']='\E[0;31m'\
        ['green']='\E[0;32m'\
        ['yellow']='\E[0;33m'\
        ['blue']='\E[0;34m'\
        ['magenta']='\E[0;35m'\
        ['cyan']='\E[0;36m'\
        ['white']='\E[0;37m'\
    );

    local defaultMSG="No message passed.";
    local defaultColor="black";
    local defaultNewLine=true;

    while [[ $# -gt 1 ]];
    do
    key="$1";

    case $key in
        -c|--color)
            color="$2";
            shift;
        ;;
        -n|--noline)
            newLine=false;
        ;;
        *)
            # unknown option
        ;;
    esac
    shift;
    done

    message=${1:-$defaultMSG};   # Defaults to default message.
    color=${color:-$defaultColor};   # Defaults to default color, if not specified.
    newLine=${newLine:-$defaultNewLine};

    echo -en "${colors[$color]}";
    echo -en "[+] "
    echo -en "$message";
    if [ "$newLine" = true ] ; then
        echo;
    fi
    tput sgr0; #  Reset text attributes to normal without clearing screen.

    return;
}

warning () {
    cecho -c 'yellow' "$@";
}

error () {
    cecho -c 'red' "$@";
}

information () {
    cecho -c 'green' "$@";
}
information " "
information " "
information "          __   __  ____   _   _  _____  _    _   _____"
information "    /\    \ \ / / / __ \ | \ | ||_   _|| |  | | / ____|"
information "   /  \    \ V / | |  | ||  \| |  | |  | |  | || (___  "
information "  / /\ \    > <  | |  | || . \` |  | |  | |  | | \___ \  "
information " / ____ \  / . \ | |__| || |\  | _| |_ | |__| | ____) |"
information "/_/    \_\/_/ \_\\ \____/ |_| \_||_____| \____/ |_____/ "
information " "
information " "

if [[ $EUID -ne 0 ]]; then
   error "This script must be run as root"
   exit 1
fi

warning "Please enter the password: "
read password
warning "Please enter storage mount path (empty for default): "
read storage_mount
storage_mount=${storage_mount%/}   # remove trailing /

information "Downloading and extracting init_host.tar.gz"
wget $INIT_HOST_TAR_GZ -O init_host.tar.gz
mkdir -p init_host
tar -pxvzf init_host.tar.gz -C ./init_host

information "Starting init_host.sh"
./init_host/init_host.sh --no-swap
rm -rf ./init_host
rm -rf init_host.tar.gz

information "Installing chef"
wget $STANDALONE_CHEF_PROVISIONER_URL -O standalone_chef_provisioner.py
python3 -u ./standalone_chef_provisioner.py $password
rm -rf ./standalone_chef_provisioner.py

information "Downloading Axonius"
wget $AXONIUS_PY_URL -O axonius.py
chmod +x ./axonius.py

if [ -z "$storage_mount" ]; then
    information "No changes needed for storage mount, passing"
else
    information "Changing storage mount to $storage_mount"
    mkdir -p /etc/systemd/system/docker.service.d/
    echo "[Service]" > /etc/systemd/system/docker.service.d/docker.root.conf
    echo "ExecStart=" >> /etc/systemd/system/docker.service.d/docker.root.conf
    echo "ExecStart=/usr/bin/dockerd -g $storage_mount/docker -H fd://" >> /etc/systemd/system/docker.service.d/docker.root.conf
    systemctl daemon-reload
    systemctl restart docker
    docker info | grep "Root Dir"
fi

information "Installing Axonius"
./axonius.py --first-time
information "Running Axonius"
python3 -u /home/ubuntu/cortex/devops/scripts/instances/start_system_on_first_boot.py

information "Done!"