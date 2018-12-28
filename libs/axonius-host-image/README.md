# Axonius Host Image
Provides all the tools necessary to run Axonius. This is not the image where containers of axonius run,
This is the image where ./axonius.sh runs!

### How to build
This should be built only via the CI system. To do this, just open a pr to develop with your changes,
and once it passes and is merged to develop it will be built automatically. If you still need to manually push it, use
this:
```
docker login # login to docker hub with axoniusdockerreadwrite
docker build -t axonius/axonius-host-image .
docker push axonius/axonius-host-image
```
