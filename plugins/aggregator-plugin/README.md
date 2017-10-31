# README #

This repository is for the AD Adapter  

### What is this repository for? ###

* AD Adapter is plugin that should connect and do actions on Active Direcotries.  
* Version - 1.0.0  

### set up ###

* In order to start the plugin you should run the ActiveDirectoryPlugin script  
* Configuration for the plugin is under ActiveDirectoryConfig.py  

### build ###
* Install latest docker version  
* Build an image and save to file by running the following commands from the dockerfile  
folder with root user:
```sh
	docker build -it axonius/ad_adapter .
	docker save -o ad_image.tar  
```
