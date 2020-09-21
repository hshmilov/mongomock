"""
Common utilities. This file should include functions that were normally put in plugin_base.py, which now makes
them not easily testable because we can not import them. Whatever is independent - put in this class.
"""
from typing import Optional

from pymongo import MongoClient

from axonius.consts.gui_consts import FEATURE_FLAGS_CONFIG
from axonius.db.db_client import get_db_client
from axonius.modules.axonius_plugins import get_axonius_plugins_singleton


class AxoniusCommon:
    def __init__(self, db: Optional[MongoClient] = None):
        self.db = db if db else get_db_client()
        self.plugins = get_axonius_plugins_singleton(db)

    def feature_flags(self) -> dict:
        return self.plugins.gui.configurable_configs[FEATURE_FLAGS_CONFIG]
