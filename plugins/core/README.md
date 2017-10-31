# Axonius #

This is the core part of the Axonius system.

## Structure ##
src - contains all the source code for the core image
tests - contains all of the tests for this repository.

## Requirements ##
* Ubuntu operating system
* docker
* python3   (automatically installed in new ubuntu's)
* pip3

## How to build ##
pull the source code to your machine.
To build and load the core image, type
```sh
sudo docker build -t axonius/core .
```

## How to run ##
Make sure you have this:

* mongodb installed and configured
* (optionally) plugin_config.ini configured inside the container.

If you didn't already create a container network do so like this:
```sh
$ docker network create axonius
```

Now, all you have to do is run the docker using the provided docker-compose instructions in the core directory:
```sh
$ docker-compose -d up
```
