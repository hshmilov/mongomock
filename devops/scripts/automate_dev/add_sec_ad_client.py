#!/usr/bin/env python3

from devops.scripts.fast_axonius.fast_axonius import fast_axonius
from test_credentials.test_ad_credentials import ad_client2_details

ax = fast_axonius()
ax.ad.add_client(ad_client2_details)
