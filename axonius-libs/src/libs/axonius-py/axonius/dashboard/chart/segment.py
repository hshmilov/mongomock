import re
from collections import defaultdict, Counter
from typing import List, Hashable
from datetime import datetime
from dataclasses import dataclass

from axonius.consts.plugin_consts import PLUGIN_NAME
from axonius.consts.adapter_consts import PREFERRED_FIELDS_PREFIX
from axonius.consts.gui_consts import (LABELS_FIELD, SPECIFIC_DATA, ADAPTERS_DATA)
from axonius.dashboard.chart.config import SortableConfig
from axonius.entities import EntityType
from axonius.modules.common import AxoniusCommon


@dataclass
class SegmentConfig(SortableConfig):

    entity: EntityType

    view: str

    field_name: str

    value_filter: List[dict]

    include_empty: bool

    @staticmethod
    def from_dict(data: dict):
        return SegmentConfig(entity=EntityType(data['entity']),
                             view=data['view'],
                             field_name=data['field']['name'],
                             value_filter=data['value_filter'],
                             include_empty=data.get('include_empty', False),
                             sort=SortableConfig.parse_sort(data))

    def generate_data(self, common: AxoniusCommon, for_date: str):
        """
        Perform aggregation which matching given view's filter and grouping by given fields, in order to get the
        number of results containing each available value of the field.
        For each such value, add filter combining the original filter with restriction of the field to this value.
        If the requested view is a pie, divide all found quantities by the total amount, to get proportions.

        :return: Data counting the amount / portion of occurrences for each value of given field, among the results
                of the given view's filter
        """

        # rpartition docs : https://docs.python.org/3.6/library/stdtypes.html#str.rpartition
        field_path_partition = self.field_name.rpartition('.')
        field_parent = field_path_partition[0] or ''
        field_name = field_path_partition[2]
        reduced_filters = self.get_reduced_filters(field_name)

        # Query and data collections according to given module
        base_view, aggregate_results = self.query_chart_segment_results(
            common, field_parent, for_date, [*reduced_filters])
        if not base_view or not aggregate_results:
            return None

        base_filter = f'({base_view["query"]["filter"]}) and ' if base_view['query']['filter'] else ''
        counted_results = self.get_counted_results(aggregate_results, reduced_filters)
        data = []
        for result_name, result_count in counted_results.items():
            if result_name == 'No Value':
                if not self.include_empty or ''.join(reduced_filters[field_name]):
                    continue
                query_filter = (f'not ({field_parent}.{field_name} == exists(true))'
                                if not field_name == LABELS_FIELD
                                else f'not ({field_name} == exists(true))')
            else:
                query_filter = self.generate_segmented_query_filter(result_name, reduced_filters,
                                                                    field_parent, field_name)
            data.append({
                'name': result_name,
                'value': result_count,
                'module': self.entity.value,
                'view': {
                    **base_view,
                    'query': {
                        'filter': f'{base_filter}{query_filter}'
                    }
                }
            })

        total = sum([x['value'] for x in data])
        return [{**x, 'portion': x['value'] / total} for x in self.perform_sort(data)]

    def get_reduced_filters(self, field_name):
        value_filter = self.value_filter
        # backward compatibility: old filters used to be strings
        if isinstance(value_filter, str):
            value_filter = [{
                'name': field_name, 'value': self.value_filter
            }]
        # remove unnamed filters
        value_filter = [x for x in value_filter if x['name']]
        # add default filter (field name with '' as value to search)
        value_filter = [{'name': field_name, 'value': ''}] + value_filter
        # create merged filter object by uniq filter key ( field name )
        reduced_filters = defaultdict(list)
        for item in value_filter:
            reduced_filters[item['name'].rpartition('.')[2]].append(item['value'])
        # remove empty search value,
        # this value if exist with another value at the same array can make the string query not valid
        for key, value in reduced_filters.items():
            if len(value) > 1:
                reduced_filters[key] = [x for x in value if x]
        return reduced_filters

    def query_chart_segment_results(self, common: AxoniusCommon, field_parent: str, date: str, filters_keys: list):
        """
        create aggregation object and return his results

        :param field_parent: field parent name
        :param date: to generate the data for
        :param filters_keys: a list of all filter by keys ( field names to filter by )
        :return: aggregation results
        """
        base_view = {'query': {'filter': '', 'expressions': []}}
        data_collection, date_query = common.data.entity_collection_query_for_date(self.entity, date)
        base_queries = [date_query] if date_query else []
        if self.view:
            base_view = common.data.find_view(self.entity, self.view)
            if not base_view or not base_view.get('view').get('query'):
                return None, None
            base_view = base_view['view']
            base_queries.append(common.query.parse_aql_filter_for_day(base_view['query']['filter'], date, self.entity))

        base_query = {'$and': base_queries} if base_queries else {}
        adapter_conditions = [{
            '$ne': ['$$i.data._old', True]
        }]
        empty_field_name = self.get_empty_field_name(field_parent, adapter_conditions)
        adapter_parent_field_name = '$adapters' + empty_field_name
        tags_parent_field_name = '$tags' + empty_field_name

        # prepare list of inputs for filtering requested data ( single or multiple fields )
        filter_inputs = []
        # prepare list of reduce function one for each field name
        unique_values_inputs = []
        # prepare name pattern
        name_pattern = {}
        # iterate and fill variables
        for index, filter_key in enumerate(filters_keys):
            name_pattern[filter_key] = {'$arrayElemAt': ['$unique_values', index]}
            unique_values_inputs.append(self.generate_aggregate_unique_values_reduce(filter_key))
            filter_inputs.append(self.generate_aggregate_combine_inputs_reduce(
                adapter_parent_field_name, tags_parent_field_name, filter_key))
        name_pattern['doc_id'] = {'$toString': '$_id'}
        query = [
            # match base queries
            {
                '$match': common.query.convert_for_aggregation_matches(data_collection, base_query)
            },
            # filter old data from adapters
            {
                '$project': {
                    'tags': {
                        '$filter': {
                            'input': '$tags',
                            'as': 'i',
                            'cond': {
                                '$eq': ['$$i.type', 'adapterdata']
                            }
                        }
                    } if LABELS_FIELD not in filters_keys else {'$map': {
                        'input': '$labels',
                        'as': 'l',
                        'in': {
                            'name': '$$l'
                        }
                    }},
                    'adapters': {
                        '$filter': {
                            'input': '$adapters',
                            'as': 'i',
                            'cond': {
                                '$and': adapter_conditions
                            }
                        }
                    },
                    PREFERRED_FIELDS_PREFIX: 1
                }
            },
            # collect all data available by filters
            {
                '$project': {
                    'collected_data': {
                        '$filter': {
                            'input': {
                                '$zip': {
                                    'inputs': filter_inputs
                                }
                            },
                            'as': 'i',
                            'cond': {
                                '$ne': ['$$i', []]
                            }
                        }
                    }
                }
            },
            # create unique array of objects representing the document data
            # each object contain a kev value pair/'s of field_name:actual_value
            {
                '$project': {
                    'unique_values': {
                        '$setUnion': [
                            {
                                '$zip': {
                                    'inputs': unique_values_inputs,
                                    'useLongestLength': True
                                }
                            }
                        ]
                    }
                }
            },
            # filter all objects containing null,
            # this can happen when no field is found in the previous stage
            # this behavior keeps the pairs synced and need to be removed in this stage and not before
            {
                '$project': {
                    'unique_values': {
                        '$filter': {
                            'input': '$unique_values',
                            'as': 'i',
                            'cond': {'$allElementsTrue': ['$$i']}
                        }
                    }
                }
            },
            # unwind to create a document for each object in the unique values array
            # we keeps the null for counting 'No Value' results
            {
                '$unwind': {
                    'path': '$unique_values',
                    'preserveNullAndEmptyArrays': True
                }
            },
            # group all documents by the unique values object to get the count
            # add extra_data array field for filtering the data
            # for each count, an object with the data will be in the array note: when the filter will be applied
            # each object that wont pass the filter should be deduct from the total count
            {
                '$group': {
                    '_id': {
                        'name': {'$ifNull': [{'$arrayElemAt': ['$unique_values', 0]}, None]},
                        'doc_id': {'$toString': '$_id'}
                    },
                    'count': {'$sum': 1},
                    'extra_data': {
                        '$push': {
                            '$cond': {
                                'if': {'$eq': [{'$arrayElemAt': ['$unique_values', 0]}, None]},
                                'then': 'No Value',
                                'else': name_pattern
                            }
                        }
                    }
                }
            }
        ]
        # execute!
        return base_view, data_collection.aggregate(query, allowDiskUse=True)

    @staticmethod
    def get_empty_field_name(field_parent, adapter_conditions):
        # prepare field parent name
        if field_parent.startswith(SPECIFIC_DATA):
            return '.' + field_parent[len(SPECIFIC_DATA) + 1:]

        if field_parent.startswith(ADAPTERS_DATA):
            # e.g. adapters_data.aws_adapter.some_field
            splitted = field_parent.split('.')
            adapter_data_adapter_name = splitted[1]

            # this condition is specific for fields that are in a specific adapter, so we
            # will not take other adapters that might share a field name (although the field itself might differ)
            adapter_conditions.append({
                '$eq': [f'$$i.{PLUGIN_NAME}', adapter_data_adapter_name]
            })
            return '.data.' + '.'.join(splitted[2:]) if len(splitted) > 2 else '.data'
        return ''

    @staticmethod
    def generate_aggregate_unique_values_reduce(key):
        """
        generate reduce object for the aggregation stage per filter
        the reduce take the collected data array and create array of object representing filter name results
        this reduce is part of zip function that will create zip version of all this reduces
        :param key: the filter name ( field name ) to
        :return: object representing one array of objects to zip
        """
        return {
            '$reduce': {
                'input': {
                    '$reduce': {
                        'input': '$collected_data',
                        'initialValue': [],
                        'in': {
                            '$concatArrays': [
                                '$$value', {
                                    '$cond': [
                                        {'$isArray': f'$$this.{key}'},
                                        f'$$this.{key}',
                                        [f'$$this.{key}']
                                    ]
                                }
                            ]
                        }
                    }
                },
                'initialValue': [],
                'in': {
                    '$concatArrays': [
                        '$$value', {
                            '$cond': {
                                'if': {'$isArray': ['$$this']},
                                'then': '$$this',
                                'else': [
                                    {
                                        '$cond': [
                                            {'$eq': [{'$type': '$$this'}, 'bool']},
                                            {'$toString': '$$this'},
                                            '$$this'
                                        ]
                                    }
                                ]
                            }
                        }
                    ]
                }
            }
        }

    @staticmethod
    def generate_aggregate_combine_inputs_reduce(field_adapter_parent, field_tags_parent, key):
        """
        generate reduce object for the aggregation stage per filter
        the reduce take the parent as array and return key value object with the filter name as key
        and the original value of the document in that key, as value
        :param field_adapter_parent: the adapter parent field name of the requested filter (field name)
        :param field_tags_parent: the tags parent field name of the requested filter (field name)
        :param key: the key to use in the reduce ( equivalent to field name )
        :return: object representing one filter reduce to be in array of reduces
        """
        field_name = field_key = key
        if field_key == LABELS_FIELD:
            field_key = 'name'
        field_prefix = ''.join(field_adapter_parent.split('.')[2:])
        return {
            '$reduce': {
                'input': {
                    '$setUnion': [
                        f'{field_adapter_parent}',
                        f'{field_tags_parent}',
                        [f'$preferred_fields.{field_prefix}' if field_prefix else '$preferred_fields']
                    ]
                },
                'initialValue': [],
                'in': {
                    '$concatArrays': [
                        '$$value', {
                            '$map': {
                                'input': {
                                    '$cond': {
                                        'if': {'$isArray': ['$$this']},
                                        'then': '$$this',
                                        'else': ['$$this']
                                    }
                                },
                                'as': 'i',
                                'in': {
                                    f'{field_name}': {'$ifNull': [f'$$i.{field_key}', None]}
                                }
                            }
                        }
                    ]
                }
            }
        }

    @staticmethod
    def get_counted_results(aggregate_results, reduced_filters):
        counted_results = Counter()
        for item in aggregate_results:
            extra_data = item.get('extra_data', [])
            if 'No Value' in extra_data:
                counted_results['No Value'] += 1
            elif SegmentConfig.match_result_item_to_filters(extra_data, reduced_filters):
                result_name = item.get('_id', {}).get('name', 'No Value')
                if not isinstance(result_name, Hashable):
                    continue
                counted_results[result_name] += 1
        return counted_results

    @staticmethod
    def match_result_item_to_filters(extra_data: list, filters: dict) -> bool:
        """
        check if the row returned from the aggregation stage is legit by requested filters
        :param extra_data: list of dicts for each count the result got in the aggregation
        :param filters: key value pair of: key -> filter (field) name, value -> list of requirements to match
        :return: boolean representing if item pass the check
        """
        # for each set of result, expected only one.
        # its because the aggregation must output a list in the group stage
        for data in extra_data:
            # for each requested filter name
            for filter_name in filters:
                # the user can ask several matches to the field
                # if one match not exist the item wont pass this test
                for match in filters[filter_name]:
                    try:
                        # we come across an error when the data in extra data is not in a form of dict
                        # wrap it in try expect and log the error for further investigations
                        value = SortableConfig.string_value_for_search(data[filter_name])
                        if match.lower() not in value:
                            return False
                    except TypeError:
                        return False
        return True

    @staticmethod
    def generate_segmented_query_filter(result_name, filters, field_parent, segmented_field_name):
        """
        generate query string for the use in devices/users page, per result given
        :param result_name: the result name of the requested segmentation
        :param filters: the filter to apply in the query string
        :param field_parent: the name of the segmented field
        :param segmented_field_name: the name of the segmented field, used to discard filters
        :return: query string composed from the segmented field query and a match query list of filters
        """
        query_filters = []
        segment_field_name = '.'.join([field_parent, segmented_field_name]) if field_parent else segmented_field_name
        segment_filter = SegmentConfig.generate_segmented_field_query_filter(segment_field_name, result_name)
        for field_name, field_value in filters.items():
            # Build the filter, according to the supported types
            if field_name == segmented_field_name:
                continue
            for value in field_value:
                if value:
                    query_filters.append(SegmentConfig.generate_segmented_field_query_filter(field_name, value, True))

        if len(query_filters) > 0:
            wrapped_query_filters = [f'({x})' for x in query_filters]
            return f'{segment_filter} and ({field_parent} == match([{" and ".join(wrapped_query_filters)}]))'
        return segment_filter

    @staticmethod
    def generate_segmented_field_query_filter(field_name, value, with_regex=False):
        """
        generate query string for one field name and value pair, can produce string for compare and contain methods
        :param field_name: field name to use in the string
        :param value: the value of compare or contain
        :param with_regex: use contain in true and compare in false
        :return: one name value pair query string
        """

        def escape_regex_value(_value):
            return re.escape(_value)

        def escape_new_line(_value):
            return _value.replace('\n', '\\n')

        query_filter = ''
        if isinstance(value, str):
            if value in ['false', 'true']:
                query_filter = f'{field_name} == {value}'
            else:
                if with_regex:
                    query_filter = f'{field_name} == regex("{escape_regex_value(value)}","i")'
                else:
                    query_filter = f'{field_name} == "{escape_new_line(value)}"'
        elif isinstance(value, (int, float)):
            query_filter = f'{field_name} == {value}'
        elif isinstance(value, datetime):
            query_filter = f'{field_name} == date("{value}")'
        return query_filter
