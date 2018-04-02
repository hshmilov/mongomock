"""
Browse "http://localhost/api/version" periodically.

This is a hack we do, to make our app load successfully;
Our design in a nutshell is an nginx server that runs uwsgi that spawns a process/thread/worker.
uwsgi doesn't need, and doesn't want to, spawn a thread before a request arrived. but we need to run our app
because the constructor does some initialization things. so we have 2 options:

1. run the app during the "import". this doesn't work. we suspect its because MongoClient() is not fork-safe
and it makes get requests not work.

2. periodically call "/api/version".

the correct solution is to change this model to a:

nginx <-> uwsgi <-> (api rest server) <- message queue -> a constantly running python.
"""
import sys
import requests
import time

URL = "http://localhost/api/version?whoami=periodic_api_version_runner"
SLEEP_COUNT = 10  # In seconds.
DEBUG = False


def debug_print(s):
    if DEBUG is True:
        s = "[periodic-api-version-runner] {0}".format(s)
        print(s)
        sys.stdout.flush()


def main():
    while True:
        try:
            debug_print("Sending get to {0}...".format(URL))
            r = requests.get(URL)
            debug_print("Got status {0}.".format(r.status_code))
        except Exception as e:
            debug_print("Got exception {0}".format(e))
        time.sleep(SLEEP_COUNT)


if __name__ == '__main__':
    sys.exit(main())
