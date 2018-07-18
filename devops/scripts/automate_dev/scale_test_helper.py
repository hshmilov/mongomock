#!/usr/bin/env python3

from devops.scripts.fast_axonius.fast_axonius import fast_axonius
from test_credentials.test_ad_credentials import ad_client2_details

from services.plugins.system_scheduler_service import SystemSchedulerService

sys_sched = SystemSchedulerService()

ax = fast_axonius()
ax.ad.add_client(ad_client2_details)
ax.stresstest.add_client({'device_count': 50000, 'name': 'blah'})
ax.stresstest_scanner.add_client({'device_count': 50000, 'name': 'blah'})

sys_sched.start_research()
