set -e

if command -v dpkg; then
  dpkg --purge cloud-init
  rm -rf /etc/cloud
else
  yum remove -y cloud-init
  rm -rf /etc/cloud
fi
