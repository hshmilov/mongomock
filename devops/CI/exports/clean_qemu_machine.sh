set -e

dpkg --purge cloud-init
rm -rf /etc/cloud /var/lib/cloud

