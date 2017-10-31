# Axonius Libs

version %%version%%.
A Docker image from which most axonius docker images will inherit.

It includes:

* python3.6 and pip3
* openresty (nginx with steroids)
* external needed python libraries
* libs
    * axonius-py

It is configured to run an nginx server that connects to your flask application with uwsgi and serves connections
in https.

### How to build

You basically don't have to build it - only inherit from it.

```bash
docker build -t axonius/axonius-libs .
```

### How to use

Inherit from your Dockerfile and add your app's code to /home/axonius/app.

Your code should have main.py with a flask app called AXONIUS_REST.

```Dockerfile
FROM $registry-url/axonius/axonius-libs

WORKDIR /home/axonius/app
ADD src .
```

This should already work, since you don't override the ENTRYPOINT and CMD directives. So if you run it:

```bash
docker run -p 443:443 myplugin
```

You will be able to access it through https://host


### How it works

The image installes all the requirements described above, and initializes uwsgi and nginx. nginx is already

configured to listen only to port 443 and serve https with a self signed certificate.

The app assumes that the uwsgi.ini file is in /home/axonius/app.

### Structure
* /home/axonius - everything is here.
* /home/axonius/app - the app main folder.
* /home/axonius/libs - libraries we use.