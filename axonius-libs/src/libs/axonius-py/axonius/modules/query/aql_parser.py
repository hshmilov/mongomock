import logging
import re
from datetime import datetime
from threading import Lock
from typing import Tuple, List, Optional

import cachetools
from frozendict import frozendict
from pymongo import MongoClient

from axonius.modules.data.axonius_data import get_axonius_data_singleton
from axonius.modules.query.consts import (OS_DISTRIBUTION_GT_SUFFIX, OS_DISTRIBUTION_LT_SUFFIX, PREFERRED_SUFFIX,
                                          NOW_PLACEHOLDER,
                                          INCLUDE_OUTDATED_TEMPLATE, EXISTS_IN_TEMPLATE)
from axonius.consts.adapter_consts import CONNECTION_LABEL, PREFERRED_FIELDS_PREFIX
from axonius.consts.gui_consts import (SAVED_QUERY_PLACEHOLDER_REGEX, OS_DISTRIBUTION_GT_LT_QUERY_REGEX,
                                       CLIENT_USED, SPECIFIC_DATA_CLIENT_USED, SPECIFIC_DATA_PLUGIN_UNIQUE_NAME,
                                       ADAPTERS_DATA, SPECIFIC_DATA)
from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME, PLUGIN_NAME
from axonius.consts.system_consts import MULTI_COMPARE_MAGIC_STRING, COMPARE_MAGIC_STRING
from axonius.devices.msft_versions import ENUM_WINDOWS_VERSIONS

from axonius.utils.datetime import parse_date
from axonius.entities import EntityType
from axonius.utils.mongo_chunked import read_chunked
from axonius.pql import find as get_mongo_query

logger = logging.getLogger(f'axonius.{__name__}')


class AQLParser:
    def __init__(self, db: Optional[MongoClient]):
        self.data = get_axonius_data_singleton(db)

    def parse(self, aql_filter: str, for_date: datetime = None) -> dict:
        if aql_filter is None:
            return {}

        aql_filter = self.parse_aql_magics(aql_filter.strip(), for_date)
        return self.convert_query_not(get_mongo_query(aql_filter)) if aql_filter else {}

    def parse_aql_magics(self, aql_filter: str, for_date: datetime = None):
        return self.parse_date(self.parse_not(self.parse_now(aql_filter, for_date)))

    def parse_for_entity(self, aql_filter: str, for_date: datetime = None, entity_type: EntityType = None) -> dict:
        if not aql_filter:
            return {}
        aql_filter = self.parse_saved_queries_ids(aql_filter, entity_type)
        if aql_filter and (OS_DISTRIBUTION_LT_SUFFIX in aql_filter or OS_DISTRIBUTION_GT_SUFFIX in aql_filter):
            aql_filter = self.parse_os_distribution_order(aql_filter)
        if aql_filter and CONNECTION_LABEL in aql_filter:
            aql_filter = self.parse_connection_labels(aql_filter)
        aql_filter = self.parse_now(aql_filter, for_date)

        return dict(self.parse_filter_cached(aql_filter))

    def parse_saved_queries_ids(self, aql_filter: str, entity_type) -> str:
        """
        This method receives a filter as string, and replace all saved queries ids with the
        actual aql if needed. Iterate the filter until no matches found - instead of iterating
        it recursively.
        :param aql_filter: filter as string
        :param entity_type:
        :return: replaces filter, or the same one.
        """
        if bool(aql_filter) and entity_type:
            matches = re.findall(SAVED_QUERY_PLACEHOLDER_REGEX, aql_filter)
            already_replaced_matches = {}
            while matches:
                for query_id in matches:
                    if already_replaced_matches.get(query_id):
                        value = already_replaced_matches[query_id]
                    else:
                        value = self.data.find_view_filter(entity_type, query_id)
                    if value:
                        aql_filter = aql_filter.replace(f'{{{{QueryID={query_id}}}}}', value)
                        if query_id not in already_replaced_matches:
                            already_replaced_matches[query_id] = value
                    else:
                        logger.error(f'ERROR: Unable to find match for query {query_id}')
                        return aql_filter
                matches = re.findall(SAVED_QUERY_PLACEHOLDER_REGEX, aql_filter)
        return aql_filter

    @staticmethod
    def parse_os_distribution_order(aql_filter: str) -> str:
        """
        Translates the relational operators '>' and '<' that are applied to os distribution to 'IN' operator
        For example: If the given input is '(specific_data.data.os.distribution > "Server 2012 R2")'
        The resulted output will contain all values of windows versions bigger than "Server 2012 R2" and
        will look like that: '(specific_data.data.os.distribution in ["10","Server 2016","Server 2019"])'
        Note! This works only for windows versions as of now.
        :param aql_filter: The filter string to translate
        """
        matcher = re.search(OS_DISTRIBUTION_GT_LT_QUERY_REGEX, aql_filter)
        while matcher:
            os_distribution = matcher.group(2)
            comp_operator = matcher.group(1)
            distribution_enum_index = ENUM_WINDOWS_VERSIONS.index(os_distribution)
            if comp_operator == '<':
                relevant_os_distributions = ENUM_WINDOWS_VERSIONS[distribution_enum_index + 1:]
            else:
                relevant_os_distributions = ENUM_WINDOWS_VERSIONS[:distribution_enum_index]
            translated_filter = 'os.distribution in [' \
                                + ','.join('"{0}"'.format(version) for version in relevant_os_distributions) + ']'
            aql_filter = aql_filter.replace(matcher.group(0), translated_filter)
            matcher = re.search(OS_DISTRIBUTION_GT_LT_QUERY_REGEX, aql_filter)

        return aql_filter

    def parse_connection_labels(self, aql_filter) -> str:
        def extract_adapter_name_from_match(match_string):
            pattern = r'plugin_name == \'(.+?)\''
            match = re.search(pattern, match_string)
            if match:
                return match.group(1)
            return ''

        def get_match_filter_strings(filter_string: str):
            """
            Returns a list of match filter string from the entire given filter string.
            For example: If the input is 'specific_data == match([plugin_name == 'active_directory_adapter'
            and (data.connection_label == "or ad")]) and (specific_data.data.name == regex("D", "i"))
            and specific_data == match([plugin_name == 'json_file_adapter' and (data.hostname == "H")])'
            The returned list would be:
            [([plugin_name == 'active_directory_adapter' and (data.connection_label == "or ad")]),
             ([plugin_name == 'json_file_adapter' and (data.hostname == "H")])]
            :param filter_string: The entire filter string to search from
            :return: List of match filter strings
            """
            match_filters_strings = []
            for m in re.finditer('match', filter_string):
                match_filter_string = '('
                index = m.end() + 1
                parentheses_weight = 1
                while parentheses_weight:
                    current_character = filter_string[index]
                    match_filter_string += current_character
                    if current_character == '(':
                        parentheses_weight += 1
                    elif current_character == ')':
                        parentheses_weight -= 1
                    index += 1
                match_filters_strings.append(match_filter_string)
            return match_filters_strings

        # Get all the client labels
        client_labels = self.data.adapter_connections_labels()

        # First of all, we need to process any connection labels that exists inside a match filter (asset entity filter)
        match_filters = get_match_filter_strings(aql_filter)

        # For each match filter, we translate every connection label filter if it appears there
        for match_filter in match_filters:
            adapter_name = extract_adapter_name_from_match(match_filter)
            translated_match_filter = self.parse_connection_label_match(match_filter, adapter_name, client_labels)
            aql_filter = aql_filter.replace(match_filter, translated_match_filter)

        return self.parse_connection_label_match(aql_filter, '', client_labels)

    @staticmethod
    def parse_connection_label_match(aql_filter: str, match_adapter_name: str, client_labels: dict) -> str:
        """
        This method finds the connection label parts in the given filter string and translates it
        :param aql_filter: The filter string to translate
        :param match_adapter_name: Adapter name of the match filter (The chosen adapter for asset entity filter)
        :param client_labels: List of all the client labels
        :return:
        """
        query_connection_label_equal = f'{CONNECTION_LABEL} =='
        query_connection_label_exist = f'{CONNECTION_LABEL} == ({{"$exists":true,"$ne":""}})))'
        query_connection_label_in = f'{CONNECTION_LABEL} in'

        def create_client_id_and_plugin_name_condition(client_id, plugin_unique_name) -> str:
            """

            Transform condition base 'specific_data.connection_label' to compound condition match build from:
             ('specific_data.client_used === <client_id> AND 'specific_data.plugin_unique_name == <plugin_unique_name>)

            :param client_id:  adapter client id
            :param plugin_unique_name: adapter unique name
            :return: transform filter string
            """
            client_used_field = CLIENT_USED if match_adapter_name else SPECIFIC_DATA_CLIENT_USED
            plugin_unique_name_field = PLUGIN_UNIQUE_NAME if match_adapter_name else SPECIFIC_DATA_PLUGIN_UNIQUE_NAME

            return f'({client_used_field} == "{client_id}" ' \
                   f'and {plugin_unique_name_field} == "{plugin_unique_name}" )'

        def create_or_separated_condition(label_conditions: list) -> str:
            """
            :param label_conditions:  list of formatted AQL connection label string ;
                                (specific_data.client_used == "http://10.0.2.149/_admin" and
                                 specific_data.plugin_unique_name == "ansible_tower_adapter_0" )
            :return: filter str  ((A) or (B) or (C))
                     return null if list input is empty
            """
            if not label_conditions:
                return None
            return f'({" or ".join(label_conditions)})'

        def create_label_condition(adapter_filter: str, label: str) -> str:
            """
            A Label can match multiple clients .
            client_info  = ( <client_id> , <plugin_unique_name> )

            :param adapter_filter: The adapter name for which the connection label filter is applied
            :param label: a AQL adapter connection label
            :return: AQL filter string compatible
            """
            # if adapter name provided, we fetch only its relevant labels, otherwise we get all labels
            relevant_labels = [client for client in client_labels.get(label, [])
                               if client and len(client) > 1 and client[1].startswith(adapter_filter)]
            labels_info = [create_client_id_and_plugin_name_condition(client_id, name) for (client_id, name) in
                           relevant_labels]
            if labels_info:
                return create_or_separated_condition(labels_info)
            return f'{SPECIFIC_DATA_CLIENT_USED} == []'

        def extract_adapter_name(filter_string: str):
            """
            Get the adapter name from the filter string.
            For example: If the input is '(adapters_data.json_file_adapter.connection_label == "some value")',
            The output will be 'json_file_adapter'.
            If no adapter data exists, an empty string is returned.
            :param filter_string: The current filter string to search from
            :return: The adapter name for which the connection label filter is applied
            """
            extracted_adapter_name = ''
            adapter_name_matcher = re.search(fr'{ADAPTERS_DATA}\.(\w+)', filter_string)
            if adapter_name_matcher:
                extracted_adapter_name = adapter_name_matcher.group(1)
            return extracted_adapter_name

        # transform operator exists with compound condition of labels filtered by selected adapter name (if selected)
        if query_connection_label_exist in aql_filter:
            exists_regexp = re.escape('({"$exists":true,"$ne":""})))')
            matcher = re.search(fr'\(\(\w+.\w+\.{CONNECTION_LABEL} == {exists_regexp}', aql_filter)
            while matcher:
                adapter_name = match_adapter_name if match_adapter_name else extract_adapter_name(matcher.group(0))
                client_labels_ids = client_labels.values()
                client_details = [create_client_id_and_plugin_name_condition(client_id, name)
                                  for ids in client_labels_ids
                                  for client_id, name in ids if name.startswith(adapter_name)]
                # If no client details were found, we send empty client details to the query so no matches will be found
                if not client_details:
                    client_details = [create_client_id_and_plugin_name_condition('', '')]
                all_connection_labels_condition = create_or_separated_condition(client_details)
                aql_filter = aql_filter.replace(matcher.group(0), all_connection_labels_condition)
                matcher = re.search(fr'\(\(\w+.\w+\.{CONNECTION_LABEL} == {exists_regexp}', aql_filter)

        # # transform operator 'in' with new compound condition per client in OR logic
        if query_connection_label_in in aql_filter:
            matcher = re.search(fr'\w+.\w+\.{CONNECTION_LABEL}' + r' in \[(.+?)\]', aql_filter)
            while matcher:
                adapter_name = match_adapter_name if match_adapter_name else extract_adapter_name(matcher.group(0))
                filter_labels = matcher.group(1)
                labels_list = [label.strip('"') for label in filter_labels.split(',')]
                label_attributes = [create_label_condition(adapter_name, label) for label in labels_list]
                aql_filter = aql_filter.replace(matcher.group(0), create_or_separated_condition(label_attributes))

                # in case of complex conditions
                matcher = re.search(fr'\w+.\w+\.{CONNECTION_LABEL}' + r' in \[(.+?)\]', aql_filter)

        # transform operator equal with compound condition to match (client_id,plugin_unique_name) tuple
        if query_connection_label_equal in aql_filter:
            matcher = re.search(fr'\w+.\w+\.{CONNECTION_LABEL} == \"(.+?)\"', aql_filter)
            while matcher:
                adapter_name = match_adapter_name if match_adapter_name else extract_adapter_name(matcher.group(0))
                aql_filter = aql_filter.replace(matcher.group(
                    0), create_label_condition(adapter_name, matcher.group(1)))
                matcher = re.search(fr'\w+.\w+\.{CONNECTION_LABEL} == \"(.+?)\"', aql_filter)

        return aql_filter

    @staticmethod
    def parse_now(aql_filter, for_date: datetime) -> str:
        if NOW_PLACEHOLDER not in aql_filter:
            return aql_filter

        now = datetime.now() if not for_date else parse_date(for_date)

        def replace_now(match):
            return match.group().replace(NOW_PLACEHOLDER, f'AXON{int(now.timestamp())}')

        # Replace "NOW - ##" to "number - ##" so AQL can further process it
        return re.sub(r'(NOW)\s*[-+]\s*(\d+)([hdw])', replace_now, aql_filter)

    @cachetools.cached(cachetools.LRUCache(maxsize=100), lock=Lock())
    def parse_filter_cached(self, aql_filter: str) -> frozendict:
        """
        See parse_filter_uncached
        """
        return self.parse_filter_uncached(aql_filter)

    def parse_filter_uncached(self, aql_filter: str) -> frozendict:
        """
        Translates a string representing of a filter to a valid MongoDB query for entities.
        This does a log of magic to support querying the regular DB

        :param aql_filter:      The PQL filter to translate into Mongo query
        :return:
        """
        if aql_filter is None:
            return frozendict({})
        include_outdated = False
        aql_filter = aql_filter.strip()
        if aql_filter.startswith(INCLUDE_OUTDATED_TEMPLATE):
            include_outdated = True
            aql_filter = aql_filter[len(INCLUDE_OUTDATED_TEMPLATE):]

        aql_filter = aql_filter.strip()
        aql_filter, enforcement_task_result_ids = self.parse_enforcement_task_results(aql_filter)
        aql_filter = self.parse_date(self.parse_not(aql_filter))
        mongo_query = self.convert_query_not(get_mongo_query(aql_filter)) if aql_filter else {}
        self.convert_query_list_fields(mongo_query, include_outdated)
        self.convert_query_field_paths(mongo_query)
        mongo_query = self.convert_query_compare(mongo_query, COMPARE_MAGIC_STRING, self.replace_query_compare)
        mongo_query = self.convert_query_compare(
            mongo_query, MULTI_COMPARE_MAGIC_STRING, self.replace_query_multi_compare)

        mongo_query = {
            '$and': [mongo_query]
        }
        if enforcement_task_result_ids is not None:
            mongo_query['$and'].append({
                'internal_axon_id': {
                    '$in': enforcement_task_result_ids
                }
            })
        return frozendict(mongo_query)

    def parse_enforcement_task_results(self, aql_filter) -> Tuple[str, Optional[List[str]]]:
        if not aql_filter.startswith(EXISTS_IN_TEMPLATE):
            return aql_filter, None

        aql_filter = aql_filter[len(EXISTS_IN_TEMPLATE):]
        recipe_id, condition, index_in_condition, entities_returned_type = (x.strip()
                                                                            for x
                                                                            in aql_filter[:aql_filter.index(')')].
                                                                            split(','))
        aql_filter = aql_filter[aql_filter.index(')') + 1:].strip()

        specific_run = self.data.tasks_collection.find_one({
            'result.metadata.pretty_id': int(recipe_id)
        })
        if not specific_run:
            return []
        result = specific_run['result']

        list_of_actions = result[condition]
        if condition == 'main':
            action = list_of_actions
        else:
            action = list_of_actions[int(index_in_condition)]
        if not action['action']['results']:
            return aql_filter, []
        return aql_filter, [x['internal_axon_id']
                            for x
                            in read_chunked(self.data.task_results_collection,
                                            action['action']['results'][entities_returned_type],
                                            projection={
                                                'chunk.internal_axon_id': 1
                                            })]

    @staticmethod
    def parse_not(aql_filter) -> str:
        matches = re.search(r'NOT\s*\[(.*)\]', aql_filter)
        while matches:
            aql_filter = aql_filter.replace(matches.group(0), f'not ({matches.group(1)})')
            matches = re.search(r'NOT\s*\[(.*)\]', aql_filter)

        return aql_filter

    @staticmethod
    def parse_date(aql_filter) -> str:
        matches = re.findall(re.compile(r'({"\$date": (.*?)})'), aql_filter)
        for match in matches:
            aql_filter = aql_filter.replace(match[0], f'date({match[1]})')

        return aql_filter

    def convert_query_not(self, mongo_query: dict):
        if isinstance(mongo_query, dict):
            translated_filter_obj = {}
            for key, value in mongo_query.items():
                if isinstance(value, dict) and '$not' in value:
                    translated_filter_obj['$nor'] = [{
                        key: self.convert_query_not(value['$not'])
                    }]
                else:
                    translated_filter_obj[key] = self.convert_query_not(value)
            return translated_filter_obj
        if isinstance(mongo_query, list):
            return [self.convert_query_not(item) for item in mongo_query]
        return mongo_query

    def convert_query_list_fields(self, mongo_query: dict, include_outdated: bool):
        """
        Post processing for the mongo query:

        1. Fixes in place the mongo filter to not include 'old' entities - if include_outdated
        2. Fixes to translate all adapters_data to use specific_data instead

        """
        if isinstance(mongo_query, dict):
            self.convert_query_specific_data(mongo_query, include_outdated)
            self.convert_query_adapter_data(mongo_query, include_outdated)

        elif isinstance(mongo_query, list):
            for x in mongo_query:
                self.convert_query_list_fields(x, include_outdated)

    def convert_query_specific_data(self, mongo_query: dict, include_outdated: bool):
        """
        Helper for convert_query_list_fields
        """
        specific_data_queries = [(k, v) for k, v in mongo_query.items() if k.startswith(SPECIFIC_DATA)]
        if specific_data_queries:
            preferred_fields_query = []
            if any(x[0].endswith(PREFERRED_SUFFIX) for x in specific_data_queries):
                preferred_fields_query = self._specific_data_to_elematch(specific_data_queries, include_outdated,
                                                                         preferred=True)
            adapters_query = self._specific_data_to_elematch(specific_data_queries, include_outdated)
            tags_query = self._specific_data_to_elematch(specific_data_queries, include_outdated)
            tags_query['$elemMatch']['$and'].append({
                'type': 'adapterdata'
            })

            elem_match = {
                '$or': [{
                    'adapters': adapters_query,
                }, {
                    'tags': tags_query
                }]
            }
            if preferred_fields_query:
                elem_match['$or'].append(*preferred_fields_query)
            mongo_query.update(elem_match)

        for k, _ in specific_data_queries:
            del mongo_query[k]

        for k, v in mongo_query.items():
            if not k.startswith(SPECIFIC_DATA):
                self.convert_query_list_fields(v, include_outdated)

    @staticmethod
    def _specific_data_to_elematch(specific_data_queries, include_outdated: bool, preferred=False):

        prefix = PREFERRED_SUFFIX if preferred else SPECIFIC_DATA
        length_of_prefix = len(prefix) + 1

        def convert_adapter_subset_query(name: str, value: object):
            # This deals with the case where we're using the GUI to select only a subset of adapters
            # to query from whilst in specific_data
            # This case leads to a very complicated output from PQL that we have to carefully fix here
            if name == SPECIFIC_DATA and isinstance(value, dict) and len(value) == 1 and list(value)[
                    0] == '$elemMatch':
                return value['$elemMatch']
            return {
                name[length_of_prefix:]: value
            }

        if preferred:
            _and = []
            for data in specific_data_queries:
                k, v = data
                _and.append({k.replace('specific_data.data', PREFERRED_FIELDS_PREFIX): v})
            return _and
        if len(specific_data_queries) == 1:
            k, v = specific_data_queries[0]

            _and = [
                convert_adapter_subset_query(k, v)
            ]
        else:
            _and = [
                {
                    '$or': [
                        convert_adapter_subset_query(k, v)
                        for k, v
                        in specific_data_queries]
                }
            ]

        _and.append({
            'pending_delete': {
                '$ne': True
            }
        })
        if not include_outdated:
            _and.append({
                'data._old': {
                    '$ne': True
                }
            })
        return {
            '$elemMatch': {
                '$and': _and
            }
        }

    def convert_query_adapter_data(self, mongo_query, include_outdated: bool):
        """
        Helper for convert_query_list_fields
        """
        adapters_data_queries = [(k, v) for k, v in mongo_query.items() if k.startswith(ADAPTERS_DATA)]
        if adapters_data_queries:
            for k, v in adapters_data_queries:
                adapters_query_count = None
                # k will look like "adapters_data.markadapter.something"
                _, adapter_name, *field_path = k.split('.')
                field_path = 'data.' + '.'.join(field_path)
                if field_path == 'data.adapter_count':
                    adapters_query = {'$exists': 1}
                    adapters_query_count = self._adapter_data_count_function(adapter_name, v)
                    include_outdated = False
                else:
                    adapters_query = self._adapter_data_to_elematch([(field_path, v)], adapter_name, include_outdated)
                tags_query = self._adapter_data_to_elematch([(field_path, v)], adapter_name, include_outdated)
                tags_query['$elemMatch']['$and'].append({
                    'type': 'adapterdata'
                })

                elem_match = {
                    '$or': [
                        {
                            'adapters': adapters_query,
                        },
                        {
                            'tags': tags_query
                        }
                    ]
                }
                if adapters_query_count is not None:
                    elem_match.get('$or')[0] = {
                        'adapters': adapters_query,
                        '$where': adapters_query_count,
                    }
                mongo_query.update(elem_match)

            for k, _ in adapters_data_queries:
                del mongo_query[k]

        for k, v in mongo_query.items():
            if not k.startswith(ADAPTERS_DATA):
                self.convert_query_list_fields(v, include_outdated)

    @staticmethod
    def _adapter_data_count_function(adapter_name, condition):
        if isinstance(condition, int):
            condition = f'count == {condition}'
        elif condition.get('$gt', None) is not None:
            condition = f'count > {condition.get("$gt")}'
        elif condition.get('$lt', None) is not None:
            condition = f'count < {condition.get("$lt")}'
        elif condition.get('$exists', None) is not None:
            condition = f'count > 0'
        elif condition.get('$in', None) is not None:
            condition = f'{str(condition.get("$in"))}.includes(count)'

        return f'''
                function() {{
                    count = 0;
                    this.adapters.forEach(adapter => {{
                        if (adapter.plugin_name == '{adapter_name}') count++;
                    }});
                    return {condition};
                }}'''

    @staticmethod
    def _adapter_data_to_elematch(adapter_data_queries, adapter_name, include_outdated: bool):
        """
        Helper for convert_query_adapter_data
        """
        _and = [
            {
                PLUGIN_NAME: adapter_name
            },
            {
                'pending_delete': {
                    '$ne': True
                }
            }
        ]
        if len(adapter_data_queries) == 1:
            k, v = adapter_data_queries[0]
            _and.append({k: v})
        else:
            _and.append({
                '$or': [
                    {
                        k: v
                    }
                    for k, v
                    in adapter_data_queries
                ]
            })

        if not include_outdated:
            _and.append({
                'data._old': {
                    '$ne': True
                }
            })
        return {
            '$elemMatch': {
                '$and': _and
            }
        }

    def convert_query_field_paths(self, mongo_query):
        """
        Now that we dropped the view db, we have to hack this!
        Converts a query that was intended for the view into a query that works on the main DB
        """
        if isinstance(mongo_query, list):
            for x in mongo_query:
                self.convert_query_field_paths(x)
            return

        if not isinstance(mongo_query, dict):
            raise Exception(f'not a dict! {mongo_query} ')

        if len(mongo_query) == 1:
            k = next(iter(mongo_query))
            v = mongo_query[k]
            if k.startswith('$'):
                self.convert_query_field_paths(v)
            elif k == 'adapters' and isinstance(v, str):
                mongo_query['$or'] = [
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
                del mongo_query[k]
            elif k == 'adapters' and isinstance(v, dict):
                operator = next(iter(v))
                if operator == '$in':
                    mongo_query['$or'] = [
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
                    del mongo_query[k]
                elif isinstance(v[operator], dict) and next(iter(v[operator])) == '$size':
                    mongo_query['$expr'] = {
                        operator: [
                            {
                                '$size': '$adapters'
                            }, v[operator]['$size']
                        ]
                    }
                    del mongo_query['adapters']

    def convert_query_compare(self, mongo_query: dict, magic: str, replace_function: callable) -> dict:
        """
        This function receives a query, check whether `magic` is in the received query dict.
        It does that by running through the dict recursively (by the types that can actually appear in it)
        if it finds the desired magic string, it passes it on to `replace_function` to process the special query,
        update the result from `convert_query_compare` and return the new process query to the system.
        :param magic: a magic string to search in the dict
        :param replace_function: a callable function to handle the part of the dict that needs to be replaced
        :param mongo_query: a dictionary with the query the user entered
        :return: a processed query that can handle regular field comparison queries in the mongoDB
        """
        if magic in mongo_query:
            return replace_function(mongo_query[magic])
        if isinstance(mongo_query, list):
            for i, list_value in enumerate(mongo_query):
                if isinstance(list_value, (list, dict)):
                    mongo_query[i] = self.convert_query_compare(list_value, magic, replace_function)
        elif isinstance(mongo_query, dict):
            for k, v in mongo_query.items():
                if isinstance(v, dict):
                    mongo_query[k] = self.convert_query_compare(v, magic, replace_function)
                if isinstance(v, list):
                    for i, list_value in enumerate(v):
                        if isinstance(list_value, (list, dict)):
                            v[i] = self.convert_query_compare(list_value, magic, replace_function)
                if k == magic:
                    mongo_query.update(replace_function(v))
                    del k
        return mongo_query

    @staticmethod
    def replace_query_multi_compare(compare_query: dict) -> dict:
        """
        This function gets a dict that represent a complex field comparison query.
        The dict should look like the following:
        {
            Operator (<,>,==): Days_Addition_or_Decline_number,
            Sub_Operator (+,-): [
                first_field_full_name,
                second_field_full_name
            ]
        }
        Which can be translated to that query (for better understanding):
        first_field_full_name + 1 < second_field_full_name
        first_field_full_name > second_field_full_name + 1
        Just like in reverse polish notation
        The function analyze each component of the query and put it in a JS filter query to be used by the mongoDB.
        :param compare_query: A part of the whole query which needs to be handled
        :return: the replacement of the received statement that mongoDB can handle
        """
        if 'Gt' in compare_query:
            main_operator = '>'
            check_number = compare_query['Gt']
            del compare_query['Gt']
        elif 'Lt' in compare_query:
            main_operator = '<'
            check_number = compare_query['Lt']
            del compare_query['Lt']
        if 'Add' in compare_query:
            sub_operator = '+'
        elif 'Sub' in compare_query:
            sub_operator = '-'
        # Extracting the two fields from the received dict
        first_field, second_field = [(compare_query[stmt][0], compare_query[stmt][1])
                                     for stmt in compare_query][0]
        # Extract the adapter name field path from the full field name
        # For example adapters_data.esx_adapter.os.distribution
        #                  ^            ^          ^
        #              Redundant     Adapter Name  Field Path
        #                 ()         (esx_adapter) ['os', 'distribution']
        _, first_adapter_name, *first_field_path = first_field.split('.')
        _, second_adapter_name, *second_field_path = second_field.split('.')
        # Joining the field path from list to string again
        first_field_path = '.'.join(first_field_path)
        second_field_path = '.'.join(second_field_path)
        return {
            '$where': f'''
            function() {{
                firstValue = "";
                secondValue = "";
                this.adapters.forEach(adapter => {{
                    if (adapter.plugin_name == '{first_adapter_name}') {{
                        if ("{first_field_path}".split('.').length > 1) {{
                            tmpVal = adapter.data;
                            "{first_field_path}".split('.').forEach(key => {{
                                if (firstValue === "" && tmpVal[key] !== undefined) tmpVal = tmpVal[key];
                                else {{
                                    firstValue = false;
                                }}
                            }})
                        }}
                        else if (adapter.data.{first_field_path} !== undefined && typeof(adapter.data.{first_field_path}.getDay) == "function") {{
                            firstValue = adapter.data.{first_field_path};
                        }}
                    }}
                    if (adapter.plugin_name == '{second_adapter_name}') {{
                        if ("{second_field_path}".split('.').length > 1) {{
                            tmpVal = adapter.data;
                            "{second_field_path}".split('.').forEach(key => {{
                                if (secondValue === "" && tmpVal[key] !== undefined) tmpVal = tmpVal[key];
                                else {{
                                    secondValue = false;
                                }}
                            }})
                        }}
                        else if (adapter.data.{second_field_path} !== undefined && typeof(adapter.data.{second_field_path}.getDay) == "function") {{
                            secondValue = adapter.data.{second_field_path};
                        }}
                    }}
                }})
                if (!firstValue || !secondValue) return false;
                firstValue.setHours(0,0,0,0);
                secondValue.setHours(0,0,0,0);
                if ("{main_operator}" == ">") {{
                    return firstValue.getTime() {main_operator} secondValue.setDate(secondValue.getDate() {sub_operator} {check_number});
                }}
                return firstValue.setDate(firstValue.getDate() {sub_operator} {check_number}) {main_operator} secondValue.getTime();
            }}
            '''
        }

    @staticmethod
    def replace_query_compare(compare_query: dict) -> dict:
        """
        This function gets a dict that represent a regular field comparison query.
        The dict should look like the following:
        {
            Operator (<,>,==): [
                first_field_full_name,
                second_field_full_name
            ]
        }
        Which can be translated to that query (for better understanding): first_field_full_name > second_field_full_name
        Just like in reverse polish notation
        The function analyze each component of the query and put it in a JS filter query to be used by the mongoDB.
        :param compare_query: A part of the whole query which needs to be handled
        :return: the replacement of the received statement that mongoDB can handle
        """
        # Translating the main operator
        if 'Eq' in compare_query:
            operator = '=='
        elif 'Gt' in compare_query:
            operator = '>'
        elif 'Lt' in compare_query:
            operator = '<'
        elif 'NotEq' in compare_query:
            operator = '!='
        elif 'GtE' in compare_query:
            operator = '>='
        elif 'LtE' in compare_query:
            operator = '<='
        # Extracting the two fields from the received dict
        first_field, second_field = [(compare_query[stmt][0], compare_query[stmt][1])
                                     for stmt in compare_query][0]
        # Extract the adapter name field path from the full field name
        # For example adapters_data.esx_adapter.os.distribution
        #                  ^            ^          ^
        #              Redundant     Adapter Name  Field Path
        #                 ()         (esx_adapter) ['os', 'distribution']
        _, first_adapter_name, *first_field_path = first_field.split('.')
        _, second_adapter_name, *second_field_path = second_field.split('.')
        # Joining the field path from list to string again
        first_field_path = '.'.join(first_field_path)
        second_field_path = '.'.join(second_field_path)
        return {
            '$where': f'''
            function() {{
                firstValue = "";
                secondValue = "";
                this.adapters.forEach(adapter => {{
                    if (adapter.plugin_name == '{first_adapter_name}') {{
                        if ("{first_field_path}".split('.').length > 1) {{
                            tmpVal = adapter.data;
                            "{first_field_path}".split('.').forEach(key => {{
                                if (firstValue === "" && tmpVal[key] !== undefined) tmpVal = tmpVal[key];
                                else {{
                                    firstValue = null;
                                }}
                            }})
                        }}
                        if (firstValue === "" && adapter.data.{first_field_path} !== undefined && typeof(adapter.data.{first_field_path}.getDay) == 'function') {{
                            firstValue = adapter.data.{first_field_path};
                            firstValue.setHours(0,0,0,0);
                            firstValue = firstValue.getTime()
                        }}
                        else if (firstValue === "" && adapter.data.{first_field_path} !== undefined) {{
                            firstValue = adapter.data.{first_field_path};
                        }}
                    }}
                    if (adapter.plugin_name == '{second_adapter_name}') {{
                        if ("{second_field_path}".split('.').length > 1) {{
                            tmpVal = adapter.data;
                            "{second_field_path}".split('.').forEach(key => {{
                                if (secondValue === "" && tmpVal[key] !== undefined) tmpVal = tmpVal[key];
                                else {{
                                    secondValue = null;
                                }}
                            }})
                        }}
                        if (secondValue === "" && adapter.data.{second_field_path} !== undefined && typeof(adapter.data.{second_field_path}.getDay) == 'function') {{
                            secondValue = adapter.data.{second_field_path};
                            secondValue.setHours(0,0,0,0);
                            secondValue = secondValue.getTime()
                        }}
                        else if (secondValue === "" && adapter.data.{second_field_path} !== undefined) {{
                            secondValue = adapter.data.{second_field_path};
                        }}
                    }}
                }})
                if (firstValue == null || secondValue == null) {{
                    return false;
                }}
                if (typeof(firstValue) === "boolean" && typeof(secondValue) === "boolean") {{
                    return firstValue == secondValue;
                }}
                if (!firstValue || !secondValue) return false;
                return firstValue {operator} secondValue;
            }}
            '''
        }


def get_aql_parser_singleton(db: Optional[MongoClient] = None) -> AQLParser:
    try:
        return get_aql_parser_singleton.instance
    except Exception:
        logger.info(f'Initiating AQLParser singleton')
        get_aql_parser_singleton.instance = AQLParser(db)

    return get_aql_parser_singleton.instance
