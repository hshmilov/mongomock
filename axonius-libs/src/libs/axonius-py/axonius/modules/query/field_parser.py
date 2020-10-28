import logging
from collections import defaultdict

from typing import Optional
from pymongo import MongoClient

from axonius.consts.adapter_consts import PREFERRED_FIELDS_PREFIX
from axonius.consts.gui_consts import HAS_NOTES, CORRELATION_REASONS, ADAPTERS_META, ADAPTERS_DATA, SPECIFIC_DATA
from axonius.consts.plugin_consts import PLUGIN_NAME, ADAPTERS_LIST_LENGTH
from axonius.modules.data.axonius_data import get_axonius_data_singleton

logger = logging.getLogger(f'axonius.{__name__}')


class FieldParser:

    def __init__(self, db: MongoClient):
        self.data = get_axonius_data_singleton(db)

    def convert_entity_data_structure(self, entity: dict, ignore_errors: bool = False) -> Optional[dict]:
        """
        Actual structure of an entity in the db is different than expected by UI for presentation.
        Here we make the conversion.

        :param entity:          Data as it came from DB
        :param ignore_errors:   Whether to fail on an error along the way
        :return:                Same data in the structure expected by UI
        """
        try:
            if entity is None:
                return None

            filtered_adapters = [adapter
                                 for adapter in entity['adapters']
                                 if adapter.get('pending_delete') is not True]

            labels = entity['labels'] if 'labels' in entity else []
            specific_data = list(filtered_adapters)
            specific_data.extend(tag
                                 for tag in entity['tags']
                                 if (ignore_errors and 'type' not in tag) or tag['type'] == 'adapterdata')
            adapters_data = defaultdict(list)
            try:
                for adapter in specific_data:
                    adapters_data[adapter[PLUGIN_NAME]].append(adapter.get('data'))
            except Exception:
                if not ignore_errors:
                    raise
                adapters_data = {}
            adapters_data = dict(adapters_data)

            adapters_meta = defaultdict(list)
            try:
                for adapter in specific_data:
                    adapters_meta[adapter[PLUGIN_NAME]].append(self.extract_adapter_metadata(adapter))
            except Exception:
                if not ignore_errors:
                    raise
                adapters_meta = {}
            adapters_meta = dict(adapters_meta)

            try:
                generic_data = [tag
                                for tag in entity['tags']
                                if tag['type'] == 'data' and 'data' in tag and tag['data'] is not False]
            except Exception:
                if not ignore_errors:
                    raise
                generic_data = []

            try:
                adapters = [adapter[PLUGIN_NAME]
                            for adapter
                            in filtered_adapters]
            except Exception:
                if not ignore_errors:
                    raise
                adapters = []

            return {
                '_id': entity.get('_id'),
                'internal_axon_id': entity.get('internal_axon_id'),
                ADAPTERS_LIST_LENGTH: entity.get(ADAPTERS_LIST_LENGTH),
                'generic_data': generic_data,
                SPECIFIC_DATA: specific_data,
                ADAPTERS_DATA: adapters_data,
                ADAPTERS_META: adapters_meta,
                CORRELATION_REASONS: entity.get(CORRELATION_REASONS),
                HAS_NOTES: entity.get(HAS_NOTES),
                'adapters': adapters,
                'labels': labels,
                PREFERRED_FIELDS_PREFIX: entity.get(PREFERRED_FIELDS_PREFIX),
                'accurate_for_datetime': entity.get('accurate_for_datetime')
            }
        except Exception:
            logger.exception(f'Failed converting {entity}, when ignoring errors = {ignore_errors}')
            # This is a legit exception, still has to be raised.
            raise

    @staticmethod
    def extract_adapter_metadata(adapter: dict) -> dict:
        """
        Extract metadata from adapter data dict, according to predefined list of fields to project

        :param adapter: All adapter data
        :return:        Requested field names and values
        """
        return {
            current_field: adapter[current_field]
            for current_field in ['client_used']
            if current_field in adapter
        }

    @staticmethod
    def convert_entity_projection_structure(projection: dict) -> Optional[dict]:
        if not projection:
            return None

        view_projection = {}
        for field, v in projection.items():
            splitted = field.split('.')

            if field in ['adapters']:
                continue
            if splitted[0] == SPECIFIC_DATA:
                splitted[0] = 'adapters'
                view_projection['.'.join(splitted)] = v
                splitted[0] = 'tags'
                view_projection['.'.join(splitted)] = v
            elif splitted[0] == ADAPTERS_DATA:
                splitted[1] = 'data'
                splitted[0] = 'adapters'
                view_projection['.'.join(splitted)] = v
                splitted[0] = 'tags'
                view_projection['.'.join(splitted)] = v
            else:
                view_projection[field] = v
        return view_projection


def get_field_parser_singleton(db: MongoClient) -> FieldParser:
    try:
        return get_field_parser_singleton.instance
    except Exception:
        logger.info(f'Initiating FieldParser singleton')
        get_field_parser_singleton.instance = FieldParser(db)

    return get_field_parser_singleton.instance
