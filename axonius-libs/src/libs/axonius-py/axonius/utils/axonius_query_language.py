import datetime
import logging
import re
from collections import defaultdict
from bson.json_util import default

from axonius.consts.adapter_consts import PREFERRED_FIELDS_PREFIX
from axonius.consts.gui_consts import (SPECIFIC_DATA, ADAPTERS_DATA, ADAPTERS_META, CORRELATION_REASONS, HAS_NOTES)
from axonius.consts.plugin_consts import PLUGIN_NAME, ADAPTERS_LIST_LENGTH
from axonius.utils.datetime import parse_date
import axonius.pql

logger = logging.getLogger(f'axonius.{__name__}')

METADATA_FIELDS_TO_PROJECT_FOR_GUI = ['client_used']
ADAPTER_PROPERTIES_DB_ENTRY = 'adapters.data.adapter_properties'
ADAPTER_LAST_SEEN_DB_ENTRY = 'adapters.data.last_seen'


def convert_to_main_db(find):
    """
    Now that we dropped the view db, we have to hack this!
    Converts a query that was intended for the view into a query that works on the main DB
    """
    if isinstance(find, list):
        for x in find:
            convert_to_main_db(x)
        return

    if not isinstance(find, dict):
        raise Exception(f'not a dict! {find} ')

    if len(find) == 1:
        k = next(iter(find))
        v = find[k]
        if k.startswith('$'):
            convert_to_main_db(v)
        elif k == 'adapters' and isinstance(v, str):
            find['$or'] = [
                {
                    'adapters.plugin_name': v
                },
                {
                    'tags': {
                        '$elemMatch': {
                            '$and': [
                                {
                                    'plugin_name': v
                                },
                                {
                                    'type': 'adapterdata'
                                }
                            ]
                        }
                    }
                }
            ]
            del find[k]
        elif k == 'adapters' and isinstance(v, dict):
            operator = next(iter(v))
            if operator == '$in':
                find['$or'] = [
                    {
                        'adapters.plugin_name': v
                    },
                    {
                        'tags': {
                            '$elemMatch': {
                                '$and': [
                                    {
                                        'plugin_name': v
                                    },
                                    {
                                        'type': 'adapterdata'
                                    }
                                ]
                            }
                        }
                    }
                ]
                del find[k]
            elif isinstance(v[operator], dict) and next(iter(v[operator])) == '$size':
                find['$expr'] = {
                    operator: [
                        {
                            '$size': '$adapters'
                        }, v[operator]['$size']
                    ]
                }
                del find['adapters']


def process_filter(filter_str, history_date):
    # Handle predefined sequence representing a range of some time units from now back
    now = datetime.datetime.now() if not history_date else parse_date(history_date)

    def replace_now(match):
        return match.group().replace('NOW', f'AXON{int(now.timestamp())}')

    # Replace "NOW - ##" to "number - ##" so AQL can further process it
    filter_str = re.sub(r'(NOW)\s*[-+]\s*(\d+)([hdw])', replace_now, filter_str)

    matches = re.search(r'NOT\s*\[(.*)\]', filter_str)
    while matches:
        filter_str = filter_str.replace(matches.group(0), f'not ({matches.group(1)})')
        matches = re.search(r'NOT\s*\[(.*)\]', filter_str)

    matches = re.findall(re.compile(r'({"\$date": (.*?)})'), filter_str)
    for match in matches:
        filter_str = filter_str.replace(match[0], f'date({match[1]})')

    return filter_str


def default_iso_date(obj):
    if isinstance(obj, datetime.datetime):
        return {'$date': obj.strftime('%m/%d/%Y %I:%M %p')}
    return default(obj)


def translate_filter_not(filter_obj):
    if isinstance(filter_obj, dict):
        translated_filter_obj = {}
        for key, value in filter_obj.items():
            if isinstance(value, dict) and '$not' in value:
                translated_filter_obj['$nor'] = [{key: translate_filter_not(value['$not'])}]
            else:
                translated_filter_obj[key] = translate_filter_not(value)
        return translated_filter_obj
    if isinstance(filter_obj, list):
        return [translate_filter_not(item) for item in filter_obj]
    return filter_obj


def extract_adapter_metadata(adapter: dict) -> dict:
    """
    extract metadata from adapter data dict, use predefined list of fields to project
    :param adapter: adapter data as dict
    :return: a dict representing the field and his value
    """
    return {current_field: adapter[current_field] for current_field
            in METADATA_FIELDS_TO_PROJECT_FOR_GUI if current_field in adapter}


# pylint: disable=R0912
def convert_db_entity_to_view_entity(entity: dict, ignore_errors: bool = False) -> dict:
    """
    Following https://axonius.atlassian.net/browse/AX-2730 we have to have to changes

    Processing of entities into a "view" once in a while is expensive and problematic.

    However we're already grew accustomed to it, and habits are hard to break.

    So this method takes an entity as it is in the db and returns

    :param ignore_errors:   Sometimes you don't want to pass a full fledged object, i.e you want
                            to pass a very narrowly projected object. In this case, this pass TRUE here,
                            and the method will ignore as many missing fields as it can.
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
            if ignore_errors:
                adapters_data = {}
            else:
                raise
        adapters_data = dict(adapters_data)

        adapters_meta = defaultdict(list)
        try:
            for adapter in specific_data:
                adapters_meta[adapter[PLUGIN_NAME]].append(extract_adapter_metadata(adapter))
        except Exception:
            if ignore_errors:
                adapters_meta = {}
            else:
                raise
        adapters_meta = dict(adapters_meta)

        try:
            generic_data = [tag
                            for tag in entity['tags']
                            if tag['type'] == 'data' and 'data' in tag and tag['data'] is not False]
        except Exception:
            if ignore_errors:
                generic_data = []
            else:
                raise

        try:
            adapters = [adapter[PLUGIN_NAME]
                        for adapter
                        in filtered_adapters]
        except Exception:
            if ignore_errors:
                adapters = []
            else:
                raise

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


def convert_db_projection_to_view(projection):
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


def parse_filter_non_entities(filter_str: str, history_date=None):
    """
    Translates a string representing of a filter to a valid MongoDB query for anything but entities
    """
    if filter_str is None:
        return {}

    filter_str = filter_str.strip()
    filter_str = process_filter(filter_str, history_date)
    res = translate_filter_not(axonius.pql.find(filter_str)) if filter_str else {}
    return res
