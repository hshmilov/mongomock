set -e

python3 ./version.zip --first-time

# This is an optimization, copying the volume may take a long time, so we copy it ahead of time.
docker create --name gui --volume gui_data:/home/axonius axonius/gui

rm -f version.zip
