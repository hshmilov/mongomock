import os

LOCAL_BUILDS_HOST = 'builds-local.axonius.lan' if 'BUILDS_HOST' not in os.environ else os.environ['BUILDS_HOST']
EXTERNAL_BUILDS_HOST = 'builds.in.axonius.com' if 'BUILDS_HOST' not in os.environ else os.environ['BUILDS_HOST']

CREDENTIALS_PATH = '/home/axonius/credentials.json'
TOKENS_PATH = '/home/axonius/tokens.json'
