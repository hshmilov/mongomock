import requests

# Read this https://axonius.atlassian.net/wiki/spaces/AX/pages/643334161/HTTPS+infrastructure+used

original_request = requests.Session.request


# for now - no verification
# TODO: Use our own CA here and create specific certificates for each plugin
def __request(*args, verify=False, **kwargs):
    return original_request(*args, verify=verify, **kwargs)


# Monkey-patching
requests.Session.request = __request
