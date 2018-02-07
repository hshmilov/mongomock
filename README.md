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

# Start empty (just mongo, core, aggregator, gui)
./axonius.sh system up

# Start basic configuration:
./axonius.sh system up --all

# Start basic configuration in debug:
./axonius.sh system up --all --debug

# Start basic configuration with ad-adpter and aws-adapter and watch plugin 
./axonius.sh system up --plugins watch --adapters ad aws

# Shutdown system (the basic configuration)
./axonius.sh system down --all

# All system commands start and stop the system [mongo, core, aggregator, gui] plus any other specified containers

# In order to start and stop a specific *container*:
./axonius.sh adapter up [--debug] ad
./axonius.sh adapter down [--debug] ad
./axonius.sh plugin up [--debug] watch
./axonius.sh plugin down [--debug] watch

./axonius.sh ls
```
