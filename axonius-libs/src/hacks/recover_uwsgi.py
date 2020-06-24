"""
As seen by many different online users that uses uwsgi, it sometimes hangs on startup
https://github.com/enowars/enochecker/pull/22
https://github.com/unbit/uwsgi/issues/1599
We couldn't determine specifically the cause for this hang but we do know how to reproduce it and how
the system looks like when it happens.
I order to reproduce it do the following
1) Create 2 instances in AWS of nodes, one master and one node
2) Connect the node to the master
3) At some point when raising all the adapters one at least one of them should get stuck in starting the container

When the container hangs what you can see is the following log lines in docker log

INFO success: uwsgi entered RUNNING state, process has stayed up for > than 1 seconds (startsecs)
INFO success: openresty entered RUNNING state, process has stayed up for > than 1 seconds (startsecs)
INFO success: python_api_version_hack entered RUNNING state, process has stayed up for > than 1 seconds (startsecs)

But no main.py running by the uwsgi and no "Hello from docker" message

Also uwsgi usually has 3 processes running if checking 'ps aux' on the system, but on the faulty containers
it has only 2 uwsgi running processes (On heavy-lifting or any other multi process container it will look differently)

After a lot of research we found that the simplest and non aggressive solution to solve this problem and making the
uwsgi stop being stuck, is sending one of his workers (not the master) a signal (SIGUSR1) which all it does according to
documentation is telling it to print statistics to the log, after that signal the uwsgi continues to work as expected.

List of signals the uwsgi processess accept are listen here:
https://uwsgi-docs.readthedocs.io/en/latest/Management.html

What this script does is searching for the first child of the uwsgi master process and signaling it with SIGUSR1
"""
import os
import sys
import psutil

UWSGI_PID_FILE_NAME = '/tmp/uwsgi.pid'
SIGUSR1 = 10


def recover():
    if not os.path.exists(UWSGI_PID_FILE_NAME):
        return True
    with open(UWSGI_PID_FILE_NAME, 'r') as fh:
        uwsgi_master_pid = int(fh.read().strip())
        parent = psutil.Process(uwsgi_master_pid)
        child = parent.children(recursive=False)
        os.kill(child[0].pid, SIGUSR1)
        return True


if __name__ == '__main__':
    SUCCESS = False
    try:
        SUCCESS = recover()
    except IndexError:
        print(f'Could find any child process of uwsgi')
    except FileNotFoundError:
        print(f'No uwsgi pid file found')
    except psutil.NoSuchProcess:
        print('Couldnt find uwsgi master process pid in running proccesses')
    except Exception as err:
        print(f'Error while trying to recover uwsgi: {err}')
    finally:
        sys.exit(int(not SUCCESS))
