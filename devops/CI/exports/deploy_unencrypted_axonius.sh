set -e

chmod +x ./version.zip
nohup ./version.zip -- --first-time
cat nohup.out

# This is an optimization, copying the volume may take a long time, so we copy it ahead of time.
docker create --name gui --volume gui_data:/home/axonius axonius/gui

rm -f version.zip
echo "Finished deploying"
