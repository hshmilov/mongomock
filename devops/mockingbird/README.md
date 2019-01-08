# Mockingbird

A server that allows creating mock environment for testing and demo purposes.

## How it works
Mockingbird creates a webserver which exposes a web API that adapters can use.
When axonius is raised with the --mock flag, AdapterBase redirects calls to the mock adapter.

## How to configure an environment
After raising the container, browse to http://<axonius>:1443

## How to run
```
./axonius.sh standalone mockingbird --restart
```

## How to run axonius with mock mode
Just append --mock 
```
e.g.
./axonius.sh system up --restart --all --mock
or
./axonius.sh adapter ad up --restart --mock
```

## How to debug
* view logs with `docker logs -f mockingbird`
* reload the python app with `docker exec mockingbird /bin/bash /app/reload_uwsgi.sh`