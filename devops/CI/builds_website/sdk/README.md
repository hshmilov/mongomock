# Builds Python SDK

Allows you to raise machines, terminate them, export them and more, everything
through python.

### How to use ###
pip install -e ./builds

```python
import builds

with builds.Builds.Instances.new() as i:
    stdout, stderr = i.ssh("ls -lah")
```

### Examples ###
Look at the examples directory and look at our CI process.