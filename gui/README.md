# Axonius Gui

The GUI for the entire system, version %version%.

It currently consists of an nginx-wsgi-flask combination as backend and bootstrap-vuejs as frontend.

### How to build

```bash
docker build -t axonius/gui .
```

### How to use
```
docker run -p 80:80 axonius/gui
```
