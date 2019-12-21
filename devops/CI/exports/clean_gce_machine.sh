set -e

dpkg --purge gce-compute-image-packages
dpkg --purge google-compute-engine-oslogin
dpkg --purge cloud-init
rm -rf /etc/cloud

