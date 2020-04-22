set -e

if command -v dpkg; then
  dpkg --purge cloud-init
  rm -rf /etc/cloud
  snap remove amazon-ssm-agent
else
  yum remove -y cloud-init
  rm -rf /etc/cloud
fi
