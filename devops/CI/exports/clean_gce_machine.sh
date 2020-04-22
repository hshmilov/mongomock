set -e

if command -v dpkg; then
  dpkg --purge gce-compute-image-packages
  dpkg --purge google-compute-engine-oslogin
  dpkg --purge cloud-init
else
  yum remove -y cloud-init google-compute-engine google-compute-engine-oslogin google-osconfig-agent
fi

rm -rf /etc/cloud

