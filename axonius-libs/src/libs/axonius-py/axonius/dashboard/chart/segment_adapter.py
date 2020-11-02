from collections import defaultdict

from dataclasses import dataclass

from axonius.dashboard.chart.config import SortableConfig
from axonius.entities import EntityType
from axonius.modules.common import AxoniusCommon
from axonius.utils.gui_helpers import get_adapters_metadata


@dataclass
class SegmentAdapterConfig(SortableConfig):

    entity: EntityType

    view: str

    @staticmethod
    def from_dict(data: dict):
        return SegmentAdapterConfig(entity=EntityType(data['entity']),
                                    view=data['selected_view'],
                                    sort=SortableConfig.parse_sort(data))

    def generate_data(self, common: AxoniusCommon, for_date: str):
        data_collection, date_query = common.data.entity_collection_query_for_date(self.entity, for_date)
        adapters_metadata = get_adapters_metadata()

        view_query_config = {'query': {'filter': '', 'expressions': []}}
        base_queries = [date_query] if date_query else []
        if self.view:
            view = common.data.find_view(self.entity, self.view) or {}
            view_query_config = view.get('view')
            if not view_query_config or not view_query_config.get('query'):
                return None
            base_queries.append(common.query.parse_aql_filter_for_day(view_query_config['query']['filter'],
                                                                      for_date, self.entity))

        condition = {'$and': base_queries} if base_queries else {}
        matching_devices = data_collection.find(condition, {'adapters.plugin_name': 1})

        total_count = matching_devices.count()
        if total_count == 0:
            return None

        count_per_adapter = defaultdict(int)
        for device_adapters in matching_devices:
            adapter_names = {adapter['plugin_name'] for adapter in device_adapters['adapters']}
            for adapter_name in adapter_names:
                count_per_adapter[adapter_name] += 1

        data = []
        query_filter = view_query_config['query']['filter']
        for adapter_name in count_per_adapter.keys():
            adapter_view = {'query': {}, 'expressions': []}
            adapter_filter = f'(adapters == \"{adapter_name}\")'
            if not query_filter:
                adapter_view['query']['filter'] = adapter_filter
            else:
                adapter_view['query']['filter'] = f'({query_filter}) and {adapter_filter}'
            data.append({
                'name': adapter_name,
                'fullName': adapters_metadata[adapter_name]['title'],
                'value': count_per_adapter[adapter_name],
                'portion': count_per_adapter[adapter_name] / total_count,
                'uniqueDevices': total_count,
                'module': self.entity.value,
                'view': adapter_view
            })
        return self.perform_sort(data, name_key='fullName')
