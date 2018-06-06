# Builds #

Our internal CI system. Allows you to do all sorts of CI things:
* create an axonius-system in 2 clicks
* export an instance to an ova file that you can immediately download anywhere (not only locally)
* see all docker images currently built.
* and more.

### How it works ###
It uses aws to create and export fully-functional instances.

### How to use ###
In our local network, just go to https://builds.axonius.local .

### How to setup my own instance ###
* Install mongodb. On windows, run the start_db.bat file to start it.
* Install python3 plus dependencies:
	* Flask
	* boto3 (aws client)
	* pymongo (mongodb python client)
	* paramiko
* run main.py.