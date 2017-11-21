import mcafee
import logging

mcafee.CREATE_LOG_FILE = True
mcafee.LOGGING_LEVEL = logging.DEBUG

import ssl

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    # Legacy Python that doesn't verify HTTPS certificates by default
    pass
else:
    # Handle target environment that doesn't support HTTPS verification
    ssl._create_default_https_context = _create_unverified_https_context

mc = mcafee.client('ec2-18-221-135-85.us-east-2.compute.amazonaws.com',
                   '8443', 'admin', 'nTiQHY3Cw6rE')
mc.help()
