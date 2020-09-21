"""
New interface for central core, that is accessible through PluginBase or as a standalone file.
Functionality from root_master.py should move to here and get deprecated eventually.
"""
import logging
from typing import Optional, Dict

from pymongo import MongoClient
from pymongo.collection import Collection

from axonius.consts.gui_consts import RootMasterNames
from axonius.consts.plugin_consts import AGGREGATOR_PLUGIN_NAME, USERS_DB, DEVICES_DB, USER_ADAPTERS_RAW_DB, \
    DEVICE_ADAPTERS_RAW_DB, USERS_FIELDS, DEVICES_FIELDS, ADAPTERS_CLIENTS_LABELS
from axonius.db.db_client import get_db_client
from axonius.entities import EntityType
from axonius.modules.common import AxoniusCommon
from axonius.utils.mongo_indices import common_db_indexes, non_historic_indexes, adapter_entity_raw_index

logger = logging.getLogger(f'axonius.{__name__}')


CENTRAL_CORE_PREFIX = 'central_core'


class CentralCore:
    def __init__(self, db: Optional[MongoClient] = None):
        self.__db = db if db else get_db_client()
        self.__axonius_common = AxoniusCommon(self.__db)
        self.entity_db_map: Dict[EntityType, Collection] = dict()
        self.raw_adapter_entity_db_map: Dict[EntityType, Collection] = dict()
        self.fields_db_map: Dict[EntityType, Collection] = dict()
        self.adapters_clients_labels_db: Optional[Collection] = None

        self.is_initialized = False

        # If Central core is not enabled, just log it
        feature_flags = self.__axonius_common.feature_flags()
        root_master_settings = feature_flags.get(RootMasterNames.root_key) or {}
        root_master_enabled = root_master_settings.get(RootMasterNames.enabled)

        if not root_master_enabled:
            logger.warning(f'Central Core not enabled. still continuing')

        self.__index_db()

    def __index_db(self):
        """
        This function must be called every time we are re-creating the central core db
        :return:
        """
        aggregator_db = self.__db[AGGREGATOR_PLUGIN_NAME]

        self.entity_db_map = {
            EntityType.Users: aggregator_db[f'{CENTRAL_CORE_PREFIX}_{USERS_DB}'],
            EntityType.Devices: aggregator_db[f'{CENTRAL_CORE_PREFIX}_{DEVICES_DB}'],
        }

        self.raw_adapter_entity_db_map = {
            EntityType.Users: aggregator_db[f'{CENTRAL_CORE_PREFIX}_{USER_ADAPTERS_RAW_DB}'],
            EntityType.Devices: aggregator_db[f'{CENTRAL_CORE_PREFIX}_{DEVICE_ADAPTERS_RAW_DB}'],
        }

        self.fields_db_map = {
            EntityType.Users: aggregator_db[f'{CENTRAL_CORE_PREFIX}_{USERS_FIELDS}'],
            EntityType.Devices: aggregator_db[f'{CENTRAL_CORE_PREFIX}_{DEVICES_FIELDS}']
        }

        self.adapters_clients_labels_db = aggregator_db[f'{CENTRAL_CORE_PREFIX}_{ADAPTERS_CLIENTS_LABELS}']

        # Now we need to ensure indexes
        for entity_type in EntityType:
            try:
                common_db_indexes(self.entity_db_map[entity_type])
                non_historic_indexes(self.entity_db_map[entity_type])
                adapter_entity_raw_index(self.raw_adapter_entity_db_map[entity_type])
            except Exception:
                logger.exception(f'Could not create central-core indexes, continuing')

        logger.info(f'Central Core db-indexing succeeded')
        self.is_initialized = True

    def promote_central_core(self):
        """
        This is a dangerous function. It effectively drops the current database collections and promotes the
        central-core ones. Use carefully
        :return:
        """
        try:
            logger.info(f'Central Core: Promoting {DEVICES_DB}')
            self.entity_db_map[EntityType.Devices].rename(DEVICES_DB, dropTarget=True)
        except Exception:
            logger.critical(f'central core - could not rename collection {DEVICES_DB}', exc_info=True)

        try:
            logger.info(f'Central Core: Promoting {USERS_DB}')
            self.entity_db_map[EntityType.Users].rename(USERS_DB, dropTarget=True)
        except Exception:
            logger.critical(f'central core - could not rename collection {USERS_DB}', exc_info=True)

        try:
            logger.info(f'Central Core: Promoting {DEVICE_ADAPTERS_RAW_DB}')
            self.raw_adapter_entity_db_map[EntityType.Devices].rename(DEVICE_ADAPTERS_RAW_DB, dropTarget=True)
        except Exception:
            logger.critical(f'central core - could not rename collection {DEVICE_ADAPTERS_RAW_DB}', exc_info=True)

        try:
            logger.info(f'Central Core: Promoting {USER_ADAPTERS_RAW_DB}')
            self.raw_adapter_entity_db_map[EntityType.Users].rename(USER_ADAPTERS_RAW_DB, dropTarget=True)
        except Exception:
            logger.critical(f'central core - could not rename collection {USER_ADAPTERS_RAW_DB}', exc_info=True)

        try:
            logger.info(f'Central Core: Promoting {DEVICES_FIELDS}')
            self.fields_db_map[EntityType.Devices].rename(DEVICES_FIELDS, dropTarget=True)
        except Exception:
            logger.critical(f'central core - could not rename collection {DEVICES_FIELDS}', exc_info=True)

        try:
            logger.info(f'Central Core: Promoting {USERS_FIELDS}')
            self.fields_db_map[EntityType.Users].rename(USERS_FIELDS, dropTarget=True)
        except Exception:
            logger.critical(f'central core - could not rename collection {USERS_FIELDS}', exc_info=True)

        try:
            logger.info(f'Central Core: Promoting {ADAPTERS_CLIENTS_LABELS}')
            self.adapters_clients_labels_db.rename(ADAPTERS_CLIENTS_LABELS, dropTarget=True)
        except Exception:
            logger.critical(f'central core - could not rename collection {ADAPTERS_CLIENTS_LABELS}', exc_info=True)

        logger.info(f'Done promoting central core. Re-indexing DB')
        self.__index_db()
