# Cortex
Where axons thrive

### How to install - Production

simply run: 
```bash
cd install
chmod 777 ./install.sh
./install.sh 
```

Notice! This will delete all tests & ci scripts, as well as git history, bash history, and more.

In order to start the system, or start (/stop) a specific container, use ./axonius.sh
Examples:
```bash

# Start empty (just mongo, core, aggregator, gui, execution)
./axonius.sh system up

# Start basic configuration:
./axonius.sh system up --all

# Start basic configuration in prod:
./axonius.sh system up --all --prod

# Start basic configuration with ad-adpter and aws-adapter and reports plugin
./axonius.sh system up --services reports --adapters ad aws

# Shutdown system (the basic configuration)
./axonius.sh system down --all

# All system commands start and stop the system plus any other specified containers
# see member axonius_services under class AxoniusService for all basic system components

# In order to start and stop a specific *container*:
./axonius.sh adapter ad up [--prod]
./axonius.sh adapter ad down [--prod]
./axonius.sh service watch up [--prod]
./axonius.sh service watch down [--prod]

# List all available adapters and services
./axonius.sh ls

# restarts the container
./axonius.sh system up --restart
# restarts the container after rebuilding images
./axonius.sh system up --restart --rebuild
# clean old volumes, rebuilds axonius-libs plus --rebuild (rebuilding images)
./axonius.sh system up --restart --hard
# pulls axonius-base-image plus --hard (clean old volumes, rebuilds axonius-libs) plus --rebuild (rebuilding images) 
./axonius.sh system up --restart --pull-base-image

# restart the GUI service *after building it with new source*
# this *does not* rebuild axonius-libs in order to be fast
./axonius.sh service gui up --restart --hard
# in order to *also* build axonius-libs use --build-libs instead
./axonius.sh service gui up --restart --build-libs
```
