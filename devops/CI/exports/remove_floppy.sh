set -e

echo "blacklist floppy" | tee /etc/modprobe.d/blacklist-floppy.conf
update-initramfs -u

