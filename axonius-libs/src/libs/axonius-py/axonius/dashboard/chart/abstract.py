from enum import Enum, auto

from dataclasses import dataclass

from axonius.consts.gui_consts import SPECIFIC_DATA, ADAPTERS_DATA
from axonius.consts.plugin_consts import PLUGIN_NAME
from axonius.dashboard.chart.config import ChartConfig
from axonius.entities import EntityType
from axonius.modules.common import AxoniusCommon
from axonius.utils.gui_helpers import find_entity_field


class AbstractFunc(Enum):
    average = auto()
    count = auto()


@dataclass
class AbstractConfig(ChartConfig):

    entity: EntityType

    view: str

    field: dict

    func: AbstractFunc

    @staticmethod
    def from_dict(data: dict):
        return AbstractConfig(entity=EntityType(data['entity']),
                              view=data['view'],
                              field=data['field'],
                              func=AbstractFunc[data['func']])

    def generate_data(self, common: AxoniusCommon, for_date: str):
        field_name = self.field['name']
        view_from_db = common.data.find_view(self.entity, self.view)
        base_view, results = self.query_chart_abstract_results(common, view_from_db, for_date)
        if not base_view or not results:
            return None
        count = 0
        sigma = 0
        for item in results:
            field_values = find_entity_field(common.query.convert_entity_data_structure(item, ignore_errors=True),
                                             field_name)
            if not field_values or (isinstance(field_values, list) and all(not val for val in field_values)):
                continue
            if self.func == AbstractFunc.count:
                count += 1
                continue
            if isinstance(field_values, list):
                count += len(field_values)
                sigma += sum(field_values)
            else:
                count += 1
                sigma += field_values

        if not count:
            return []
        view_name = view_from_db['name'] if self.view else 'ALL'
        data = {
            'name': f'{self.func.name} of {self.field["title"]} on {view_name} results',
            'value': count,
            'view': base_view,
            'module': self.entity.value,
        }
        if self.func == AbstractFunc.average:
            data['value'] = sigma / count
            data['schema'] = self.field
        return [data]

    def query_chart_abstract_results(self, common: AxoniusCommon, view_from_db, date: str):
        """
        Build the query and retrieve data for calculating the abstract chart for given field and view
        """
        splitted = self.field['name'].split('.')
        additional_elemmatch_data = {}

        if splitted[0] == SPECIFIC_DATA:
            processed_field_name = '.'.join(splitted[1:])
        elif splitted[0] == ADAPTERS_DATA:
            processed_field_name = 'data.' + '.'.join(splitted[2:])
            additional_elemmatch_data = {
                PLUGIN_NAME: splitted[1]
            }
        else:
            raise ValueError(f'Chart defined with unsupported field {self.field["name"]}')

        adapter_field_name = 'adapters.' + processed_field_name
        tags_field_name = 'tags.' + processed_field_name

        base_view = {'query': {'filter': ''}}
        base_query = {
            '$or': [
                {
                    'adapters': {
                        '$elemMatch': {
                            processed_field_name: {
                                '$exists': True
                            },
                            **additional_elemmatch_data
                        }
                    }
                },
                {
                    'tags': {
                        '$elemMatch': {
                            processed_field_name: {
                                '$exists': True
                            },
                            **additional_elemmatch_data
                        }
                    }
                }
            ]
        }
        data_collection, date_query = common.data.entity_collection_query_for_date(self.entity, date)
        if date_query:
            base_query = {'$and': [base_query, date_query]}

        if view_from_db:
            base_view = view_from_db['view']
            if not base_view or not base_view.get('query'):
                return None, None
            base_query = {
                '$and': [
                    common.query.parse_aql_filter_for_day(base_view['query']['filter'], date, self.entity),
                    base_query
                ]
            }
            base_view['query']['filter'] = f'({base_view["query"]["filter"]}) and '

        field_compare = 'true' if self.field['type'] == 'bool' else 'exists(true)'
        if self.field['type'] in ['number', 'integer']:
            field_compare = f'{field_compare} and {self.field["name"]} > 0'
        base_view['query']['filter'] = f'{base_view["query"]["filter"]}{self.field["name"]} == {field_compare}'

        return base_view, data_collection.find(base_query, projection={
            adapter_field_name: 1,
            tags_field_name: 1,
            f'adapters.{PLUGIN_NAME}': 1,
            f'tags.{PLUGIN_NAME}': 1
        })
