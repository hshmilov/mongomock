#!/usr/bin/env python3

from services.plugins.system_scheduler_service import SystemSchedulerService

SYSTEM_SCHEDULER = SystemSchedulerService()
SYSTEM_SCHEDULER.start_research()
