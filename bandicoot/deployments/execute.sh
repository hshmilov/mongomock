docker run  --network=axonius -it bandicoot:1.0 ./main transfer --mgHostname mongo.axonius.local --pgHostname postgres  --pgPort 5432 --transferDevices=false --transferAdapters=true