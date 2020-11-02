from typing import List
from dataclasses import dataclass

from axonius.dashboard.chart.base import ChartConfig
from axonius.entities import EntityType
from axonius.modules.common import AxoniusCommon


@dataclass
class IntersectConfig(ChartConfig):

    base: str

    entity: EntityType

    intersecting: List[str]

    @staticmethod
    def from_dict(data: dict):
        return IntersectConfig(base=data['base'],
                               entity=EntityType(data['entity']),
                               intersecting=data['intersecting'])

    def generate_data(self, common: AxoniusCommon, for_date: str):
        if not self.intersecting or not len(self.intersecting):
            raise Exception('Intersection chart requires at least one view')

        data_collection, date_query = common.data.entity_collection_query_for_date(self.entity, for_date)
        base = {
            'name': 'ALL',
            'view': {'query': {'filter': '', 'expressions': []}},
            'remainder': True,
            'module': self.entity.value,
            'value': 0,
            'portion': 0,
            'index_in_config': 0
        }
        base_queries = [date_query] if date_query else []
        if self.base:
            base_from_db = common.data.find_view(self.entity, self.base)
            if not base_from_db or not base_from_db.get('view', {}).get('query'):
                return None
            base['view'] = base_from_db['view']
            base['name'] = base_from_db.get('name', '')
            base_queries.append(common.query.parse_aql_filter_for_day(base['view']['query']['filter'],
                                                                      for_date, self.entity))

        data = []
        total = common.query.count_matches(data_collection, {'$and': base_queries} if base_queries else {})
        if not total:
            return [base]
        base_filter = f'({base["view"]["query"]["filter"]}) and ' if base['view']['query']['filter'] else ''

        child1_from_db = common.data.find_view(self.entity, self.intersecting[0])
        if not child1_from_db or not child1_from_db.get('view', {}).get('query'):
            return None
        child1 = {
            'name': child1_from_db.get('name', ''),
            'view': child1_from_db['view'],
            'module': self.entity.value,
            'index_in_config': 1
        }
        child1_filter = child1['view']['query']['filter']
        child1_query = common.query.parse_aql_filter_for_day(child1_filter, for_date, self.entity)
        child2_filter = ''
        if len(self.intersecting) == 1:
            # Fetch the only child, intersecting with parent
            child1['view']['query']['filter'] = f'{base_filter}({child1_filter})'
            child1['value'] = common.query.count_matches(data_collection, {
                '$and': base_queries + [child1_query]
            })
            child1['portion'] = child1['value'] / total
            data.append(child1)
        else:
            child2_from_db = common.data.find_view(self.entity, self.intersecting[1])
            if not child2_from_db or not child2_from_db.get('view', {}).get('query'):
                return None
            child2 = {
                'name': child2_from_db.get('name', ''),
                'view': child2_from_db['view'],
                'module': self.entity.value,
                'index_in_config': 2
            }
            child2_filter = child2['view']['query']['filter']
            child2_query = common.query.parse_aql_filter_for_day(child2_filter, for_date, self.entity)

            # Child1 + Parent - Intersection
            child1['view']['query']['filter'] = f'{base_filter}({child1_filter}) and not ({child2_filter})'
            child1['value'] = common.query.count_matches(data_collection, {
                '$and': base_queries + [
                    child1_query, {
                        '$nor': [child2_query]
                    }]
            })
            child1['portion'] = child1['value'] / total
            data.append(child1)

            # Intersection
            numeric_value = common.query.count_matches(data_collection, {
                '$and': base_queries + [
                    child1_query, child2_query
                ]
            })
            data.append({
                'name': f'{child1["name"]} + {child2["name"]}',
                'intersection': True,
                'value': numeric_value,
                'portion': numeric_value / total,
                'view': {**base['view'], 'query': {'filter': f'{base_filter}({child1_filter}) and ({child2_filter})'}},
                'module': self.entity.value
            })

            # Child2 + Parent - Intersection
            child2['view']['query']['filter'] = f'{base_filter}({child2_filter}) and not ({child1_filter})'
            child2['value'] = common.query.count_matches(data_collection, {
                '$and': base_queries + [
                    child2_query, {
                        '$nor': [child1_query]
                    }]
            })
            child2['portion'] = child2['value'] / total
            data.append(child2)

        base['portion'] = 1 - sum([x['portion'] for x in data])
        base['value'] = total - sum([x['value'] for x in data])
        if child2_filter:
            child1_filter = f'({child1_filter}) or ({child2_filter})'
        base['view']['query']['filter'] = f'{base_filter}not ({child1_filter})'
        return [base, *data]
