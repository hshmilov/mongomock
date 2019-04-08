# Builds #

Our internal CI system. Allows you to do all sorts of CI things:
* Create an axonius-system in 2 clicks
* Create a demo in 2 clicks
* Export an instance to an ova file that you can immediately download anywhere (not only locally)
* and more

### How it works ###
It uses aws/gcp to create and export fully-functional instances.

### How to use ###
just go to https://builds.in.axonius.com. For debugging only, use https://builds-local.axonius.lan

### How to install (One time)###
* Make sure you have an ubuntu 16/18 with docker and docker-compose installed
* update credentials.json

### Production use ###
```./run.sh```

### Debug use ###
Note! This exposes your db to the public, runs less threads and not running the periodic instance monitor.
```./run.sh debug```
