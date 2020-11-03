"""
Common utilities. This file should include functions that were normally put in plugin_base.py, which now makes
them not easily testable because we can not import them. Whatever is independent - put in this class.
Use this as an entry point for different namespaces which are needed throughout the system.
The namespaces should depend on only on a DB connection, as well as every level within it.
The goal being that there are no dependencies between different namespaces.
"""
from datetime import datetime
from typing import Optional, Dict

from bson import ObjectId
from pymongo import MongoClient

from axonius.consts.gui_consts import FEATURE_FLAGS_CONFIG
from axonius.consts.plugin_consts import AUDIT_COLLECTION, CORE_UNIQUE_NAME
from axonius.db.db_client import get_db_client
from axonius.logging.audit_helper import AuditType
from axonius.modules.axonius_plugins import get_axonius_plugins_singleton
from axonius.modules.data.axonius_data import get_axonius_data_singleton
from axonius.modules.query.axonius_query import get_axonius_query_singleton


class AxoniusCommon:
    def __init__(self, db: Optional[MongoClient] = None):
        self.db = db if db else get_db_client()
        self.plugins = get_axonius_plugins_singleton(db)
        self.data = get_axonius_data_singleton(db)
        self.query = get_axonius_query_singleton(db)

    def feature_flags(self) -> dict:
        return self.plugins.gui.configurable_configs[FEATURE_FLAGS_CONFIG]

    @property
    def audit_collection(self):
        return self.db.get_database(CORE_UNIQUE_NAME).get_collection(AUDIT_COLLECTION)

    def add_activity_msg(self, category: str, action: str, params: Dict[str, str], activity_type: AuditType,
                         user_id: ObjectId = None):
        """
            category: String representation of the category
            action: String representation of the action
            params: Specifying subject of the activity
            activity_type: Indicating the source of the activity
            user_id: The user performing the activity - leave empty for system activity

        """
        new_activity_log = dict(category=category,
                                action=action,
                                params=params,
                                timestamp=datetime.now(),
                                user=user_id,
                                type=activity_type.value)

        self.audit_collection.insert_one(new_activity_log)
