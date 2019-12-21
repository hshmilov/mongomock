set -e
dpkg --purge cloud-init
rm -rf /etc/cloud
snap remove amazon-ssm-agent

