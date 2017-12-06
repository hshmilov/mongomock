# Axonius Base Image
version %%version%%.
A Docker image from which axonius-libs docker image will inherit.
It contains all executables we need in each container, but not code.

### How to use
This image is currently not built in our CI system.
We need to manually push it to the docker hub on each change:
```sh
docker login    # login to docker hub
docker push axonius/axonius-base-image
```

and then docker pull axonius/axonius-base-image whereever we use
axonius/axonius-libs.
