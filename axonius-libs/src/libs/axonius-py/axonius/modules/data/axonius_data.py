import logging
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

from bson import ObjectId
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.cursor import Cursor

from axonius.consts.adapter_consts import CLIENT_ID, CONNECTION_LABEL
from axonius.consts.gui_consts import DASHBOARD_COLLECTION
from axonius.consts.plugin_consts import USERS_DB, DEVICES_DB, HISTORICAL_USERS_DB_VIEW, HISTORICAL_DEVICES_DB_VIEW, \
    ADAPTERS_CLIENTS_LABELS, USER_VIEWS, DEVICE_VIEWS, PLUGIN_UNIQUE_NAME
from axonius.consts.report_consts import TASKS_RESULTS_COLLECTION, TASKS_COLLECTION
from axonius.entities import EntityType
from axonius.modules.axonius_plugins import get_axonius_plugins_singleton

logger = logging.getLogger(f'axonius.{__name__}')


class AxoniusData:
    def __init__(self, db: Optional[MongoClient] = None):
        self.plugins = get_axonius_plugins_singleton(db)

    @property
    def entity_data_collection(self):
        return {
            EntityType.Devices: self.plugins.aggregator.plugin_db[DEVICES_DB],
            EntityType.Users: self.plugins.aggregator.plugin_db[USERS_DB]
        }

    @property
    def entity_history_collection(self):
        return {
            EntityType.Devices: self.plugins.aggregator.plugin_db[HISTORICAL_DEVICES_DB_VIEW],
            EntityType.Users: self.plugins.aggregator.plugin_db[HISTORICAL_USERS_DB_VIEW]
        }

    @property
    def history_dates_by_entity(self):
        def _get_dates_map(dates_list):
            return {
                d.date().isoformat(): d
                for d in dates_list
            }

        return {
            key: _get_dates_map(value.distinct('accurate_for_datetime'))
            for key, value in self.entity_history_collection.items()
        }

    @property
    def entity_views_collection(self):
        return {
            EntityType.Devices: self.plugins.gui.plugin_db[DEVICE_VIEWS],
            EntityType.Users: self.plugins.gui.plugin_db[USER_VIEWS]
        }

    @property
    def dashboard_collection(self):
        return self.plugins.gui.plugin_db[DASHBOARD_COLLECTION]

    @property
    def connection_labels_collection(self):
        return self.plugins.aggregator.plugin_db[ADAPTERS_CLIENTS_LABELS]

    @property
    def tasks_collection(self):
        return self.plugins.enforcer.plugin_db[TASKS_COLLECTION]

    @property
    def task_results_collection(self):
        return self.plugins.enforcer.plugin_db[TASKS_RESULTS_COLLECTION]

    def entity_collection_query_for_date(self, entity_type: EntityType, date: str = None) -> Tuple[Collection, dict]:
        """
        If no date provided, return the current data collection.
        Otherwise, return the collection designated to requested day, if exists.
        Otherwise, return aggregated history collection and the relevant date to fecth by.

        :param entity_type: For the data collection
        :param date:        For the relevant data, formatted YYYY-MM-DD
        :return:
        """
        if not date:
            return self.entity_data_collection[entity_type], {}

        history_date_collection_name = f'historical_{entity_type.value}_{date.replace("-", "_")}'
        if history_date_collection_name in self.plugins.aggregator.plugin_db.list_collection_names():
            return self.plugins.aggregator.plugin_db[history_date_collection_name], {}

        return self.entity_history_collection[entity_type], {
            'accurate_for_datetime': self.history_dates_by_entity[entity_type][date]
        }

    def adapter_connections_labels(self) -> Dict[str, List[Tuple[str, str]]]:
        """
        Fetch all user defined Connection Labels
        :return: Mapping of each saved label to the list of distinct clients labeled by it
        """
        label_to_connections = defaultdict(list)
        labels_list = self.connection_labels_collection.find({})
        for label in labels_list:
            client_id = label.get(CLIENT_ID)
            connection_label = label.get(CONNECTION_LABEL)
            plugin_unique_name = label.get(PLUGIN_UNIQUE_NAME)

            if client_id and connection_label and plugin_unique_name:
                label_to_connections[connection_label].append((client_id, plugin_unique_name))
        return label_to_connections

    def find_view(self, entity_type: EntityType, view_id: str, project: Dict[str, bool] = None):
        if not view_id:
            return None
        view_doc = self.entity_views_collection[entity_type].find_one({
            '_id': ObjectId(view_id)
        }, projection=project)
        return view_doc

    def find_view_filter(self, entity_type: EntityType, view_id: str) -> str:
        """
        :param entity_type: View was saved for
        :param view_id:     Unique id to fetch by
        :return:            The filter saved for the given view_id of entity_type
        """
        view_doc = self.find_view(entity_type, view_id, {
            'view.query.filter': True
        }) or {}
        return view_doc.get('view', {}).get('query', {}).get('filter', '')

    def find_view_name(self, entity_type: EntityType, view_id: str) -> str:
        view_doc = self.find_view(entity_type, view_id, {
            'name': True,
            '_id': False
        })
        return view_doc['name'] if view_doc else None

    def find_views(self, entity_type: EntityType, view_filter: dict = None, project: Dict[str, bool] = None) -> Cursor:
        """
        :param entity_type: View was saved for
        :param view_find:   Mongo query to search the view by
        :return:            Cursor or found results
        """
        return self.entity_views_collection[entity_type].find(view_filter or {}, projection=project)

    def find_views_by_name_match(self, name_match):
        """
        :param name_match:  To search for views by
        :return:            UUIDs for all views whose name contains name_match
        """
        views_match = []
        for entity_type in EntityType:
            views_match.extend(str(view['_id']) for view in self.find_views(entity_type, {
                'name': {
                    '$regex': name_match,
                    '$options': 'i'
                }
            }, {
                '_id': True
            }))
        return views_match

    def find_chart(self, chart_id: str):
        chart_doc = self.dashboard_collection.find_one({
            '_id': ObjectId(chart_id)
        })
        if not chart_doc:
            logger.error(f'Chart {chart_id} not found')
        return chart_doc


def get_axonius_data_singleton(db: Optional[MongoClient] = None):
    try:
        return get_axonius_data_singleton.instance
    except Exception:
        logger.info(f'Initiating AxoniusData singleton')
        get_axonius_data_singleton.instance = AxoniusData(db)

    return get_axonius_data_singleton.instance
