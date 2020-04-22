set -e

if command -v dpkg; then
  dpkg --purge cloud-init
  rm -rf /etc/cloud /var/lib/cloud
else
  yum remove -y cloud-init
  rm -rf /etc/cloud /var/lib/cloud
fi
