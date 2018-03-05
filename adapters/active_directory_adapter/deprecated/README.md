## PSExec

These files were used when we ran code using rpc. We will need them in the future.

This whole code has to be rewritten again, note that!

Among the errors it has:
* new service is not stopped and deleted at the end
* new service name is random
* new filename is random
* output file is not being deleted
* getfile for large files might fail
* getfile and putfile for absolute paths (including drive) do not work
* no retry anywhere

and more