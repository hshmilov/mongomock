from typing import List
from dataclasses import dataclass

from axonius.dashboard.chart.config import SortableConfig
from axonius.entities import EntityType
from axonius.modules.common import AxoniusCommon


@dataclass
class CompareConfig(SortableConfig):

    views: List[dict]

    @staticmethod
    def from_dict(data: dict):
        return CompareConfig(views=data['views'],
                             sort=SortableConfig.parse_sort(data))

    def generate_data(self, common: AxoniusCommon, for_date: str):
        if not self.views:
            raise Exception('Comparison chart requires at least one view')

        data = []
        total = 0
        for i, view in enumerate(self.views):
            entity_name = view.get('entity', EntityType.Devices.value)
            entity = EntityType(entity_name)
            view_id = view['id']
            view_from_db = common.data.find_view(entity, view_id)
            if not view_from_db:
                continue

            view = view_from_db['view']
            data_item = {
                'view_id': view_id,
                'name': view_from_db['name'],
                'view': view,
                'module': entity_name,
                'value': 0,
                'index_in_config': i
            }
            data_collection, date_query = common.data.entity_collection_query_for_date(entity, for_date)
            query = common.query.parse_aql_filter_for_day(view['query']['filter'], for_date, entity)
            if date_query:
                query = {
                    '$and': [query, date_query]
                }
            data_item['value'] = common.query.count_matches(data_collection, query)
            data.append(data_item)
            total += data_item['value']

        return [{
            **x, 'portion': (x['value'] / total if total else 0)
        } for x in self.perform_sort(data)]
