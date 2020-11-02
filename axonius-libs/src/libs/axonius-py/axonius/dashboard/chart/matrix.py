from collections import defaultdict
from typing import List
from dataclasses import dataclass

from axonius.dashboard.chart.config import SortableConfig
from axonius.entities import EntityType
from axonius.modules.common import AxoniusCommon


@dataclass
class MatrixConfig(SortableConfig):

    entity: EntityType

    base: List[str]

    intersecting: List[str]

    @staticmethod
    def from_dict(data: dict):
        return MatrixConfig(entity=EntityType(data['entity']),
                            base=data['base'],
                            intersecting=data['intersecting'],
                            sort=SortableConfig.parse_sort(data))

    def generate_data(self, common: AxoniusCommon, for_date: str):
        data_collection, date_query = common.data.entity_collection_query_for_date(self.entity, for_date)
        data = []
        total_values = defaultdict(int)
        for base_query_index, base_query_id in enumerate(self.base):
            base_filter = ''
            base_name = f'All {self.entity.value}'
            if base_query_id:
                base_from_db = common.data.find_view(self.entity, base_query_id)
                if not base_from_db or not base_from_db.get('view', {}).get('query'):
                    continue
                base_name = base_from_db['name']
                base_filter = base_from_db['view']['query']['filter']

            # intersection of base query with each data query
            for intersecting_query_index, intersecting_query_id in enumerate(self.intersecting):
                child_from_db = common.data.find_view(self.entity, intersecting_query_id)
                if not child_from_db or not child_from_db.get('view', {}).get('query'):
                    continue
                current_data = {
                    'name': base_name,
                    'module': self.entity.value,
                    'baseIndex': base_query_index,
                    'intersectionIndex': intersecting_query_index,
                    'intersectionName': child_from_db['name'],
                    'view': child_from_db['view']
                }
                intersection_filter = current_data['view']['query']['filter']
                if base_filter:
                    intersection_filter = f'({base_filter}) and ({intersection_filter})'
                current_data['view']['query'] = {
                    'expressions': [],
                    'filter': intersection_filter
                }
                query = common.query.parse_aql_filter_for_day(intersection_filter, for_date, self.entity)
                current_data['numericValue'] = data_collection.count_documents({
                    '$and': [date_query, query]
                } if date_query else query)
                total_values[base_query_index] += current_data['numericValue']
                data.append(current_data)

        return self.perform_sort(self.format_data(data, total_values).values())

    @staticmethod
    def format_data(data, total_values):
        total = sum(total_values.values())
        # no intersections found - return an empty response
        if not total:
            return {}

        intersected_data = {}
        for data_entry in data:
            data_entry['value'] = total_values[data_entry['baseIndex']]
            data_entry['portion'] = data_entry['value'] / total

            if not data_entry.get('numericValue'):
                continue

            if not intersected_data.get(data_entry['baseIndex']):
                intersected_data[data_entry['baseIndex']] = {
                    'name': data_entry.get('name'),
                    'intersections': [],
                    'value': data_entry.get('value')
                }
            current_intersections = intersected_data[data_entry['baseIndex']].get('intersections')
            current_intersections.append({
                'name': data_entry.get('intersectionName'),
                'intersectionIndex': data_entry.get('intersectionIndex'),
                'value': data_entry.get('numericValue'),
                'view': data_entry.get('view'),
                'module': data_entry.get('module'),
                'index': len(current_intersections)
            })
        return intersected_data
