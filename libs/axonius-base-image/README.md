# Axonius Base Image
version %%version%%.
A Docker image from which axonius-libs docker image will inherit.
It contains all executables we need in each container, but not code.
Usually, what we do here is to add pip3 and pip2 packages, apt-get packages, etc.

### How to use
This image is currently not built in our CI system.
We need to manually push it to the docker hub on each change.
Notice! Once you push it to the system you affect everyone!

How to:
```sh
docker login    # login to docker hub with axoniusdockerreadwrite
docker build -t aoxnius/axonius-base-image .
docker push axonius/axonius-base-image
```

afterwards, rebuild axonius/axonius-libs and your images with ../../prepare_ci_env.sh .
