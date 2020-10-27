import logging
from datetime import datetime

from typing import Optional
from pymongo import MongoClient
from pymongo.collection import Collection

from axonius.entities import EntityType
from axonius.modules.data.axonius_data import get_axonius_data_singleton
from axonius.modules.query.aql_parser import get_aql_parser_singleton

logger = logging.getLogger(f'axonius.{__name__}')


class AxoniusQuery:
    def __init__(self, db: Optional[MongoClient] = None):
        self.data = get_axonius_data_singleton(db)
        self.aql_parser = get_aql_parser_singleton(db)

    def parse_aql_filter(self, aql_filter: str, for_date: datetime = None, entity_type: EntityType = None):
        return self.aql_parser.parse(aql_filter, for_date, entity_type)

    def parse_aql_filter_for_day(self, aql_filter: str, date: str = None, entity_type: EntityType = None):
        if date:
            date_datetime = datetime.strptime(date, '%Y-%m-%d')
            now_time = datetime.now().time()
            date = datetime.combine(date_datetime, now_time)
        return self.parse_aql_filter(aql_filter, date, entity_type)

    @staticmethod
    def is_where_query(query):
        return '\'$where\': ' in str(query)

    def count_matches(self, data_collection: Collection, query: dict) -> int:
        if self.is_where_query(query):
            return data_collection.count(query)
        return data_collection.count_documents(query)

    def convert_for_aggregation_matches(self, data_collection: Collection, query: dict) -> dict:
        if not self.is_where_query(query):
            return query
        return {
            '_id': {
                '$in': [
                    x['_id'] for x in data_collection.find(query, projection={'_id': True})
                ]
            }
        }


def get_axonius_query_singleton(db: Optional[MongoClient] = None):
    try:
        return get_axonius_query_singleton.instance
    except Exception:
        logger.info(f'Initiating AxoniusQuery singleton')
        get_axonius_query_singleton.instance = AxoniusQuery(db)

    return get_axonius_query_singleton.instance
