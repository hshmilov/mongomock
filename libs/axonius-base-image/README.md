# Axonius Base Image
This is what each and every axonius container inherits from (all adapters, all services, etc) , via axonius-libs.

e.g.:
```
<axonius/axonius-base-image>
       ^
       |
       |
<axonius/axonius-libs>
       ^
       |
       |
<axonius/aws-adapter>
```

It contains all executables we need in each container, but not code.
Usually, what we do here is to add pip3 and pip2 packages, apt-get packages, etc.

### How to build
This should be built only via the CI system. To do this, just open a pr to develop with your changes,
and once it passes and is merged to develop it will be built automatically. If you still need to manually push it, use
this:
```sh
docker login    # login to docker hub with axoniusdockerreadwrite
docker build -t axonius/axonius-base-image .
docker push axonius/axonius-base-image
```
