from abc import abstractmethod
from datetime import datetime
from enum import Enum, auto

from dataclasses import dataclass
from dataclasses_json import DataClassJsonMixin

from axonius.modules.common import AxoniusCommon


class ChartSortBy(Enum):
    """
    Possible values to sort by
    """
    name = auto()
    value = auto()


class ChartSortOrder(Enum):
    """
    Possible directions to order the sort
    """
    desc = auto()
    asc = auto()


@dataclass
class ChartConfig(DataClassJsonMixin):
    """
    A configuration of a chart defines the properties needed to calculate its data.
    """

    @abstractmethod
    def generate_data(self, common: AxoniusCommon, for_date: str):
        """
        To implement in inheriting config, according to the type

        :param common: Data source and helpers for querying it
        :param for_date: The day to calculate data for, in isoformat
        :return: List of data defining portions, titles and queries needed to display the chart
        """

    @staticmethod
    def string_value_for_search(value):
        if isinstance(value, datetime):
            return value.strftime('%a, %d %b %Y %H:%M:%S GMT').lower()
        return str(value).lower()


@dataclass
class ChartSort(DataClassJsonMixin):
    """
    Method and direction of sorting to perform on a data of a supporting chart configuration
    """

    sort_by: ChartSortBy

    sort_order: ChartSortOrder

    @staticmethod
    def from_dict(data: dict):
        return ChartSort(ChartSortBy[data['sort_by']], ChartSortOrder[data['sort_order']])


@dataclass
class SortableConfig(ChartConfig):
    """
    A configuration of a chart that supports sorting of its data
    """

    sort: ChartSort

    @abstractmethod
    def generate_data(self, common: AxoniusCommon, for_date: str):
        pass

    @staticmethod
    def parse_sort(data: dict):
        return ChartSort.from_dict(data['sort'])

    def apply_sort(self, sort_by: str, sort_order: str):
        if sort_by:
            self.sort.sort_by = ChartSortBy[sort_by]
        if sort_order:
            self.sort.sort_order = ChartSortOrder[sort_order]

    def perform_sort(self, data, name_key=None):
        """
        Performs the sort on given data, as dictated by the current sort.
        Selected sort_by is the primary key with the other as secondary key.
        Selected order_by is the direction of the sort.

        :param data: To be sorted
        :param name_key: Alternate key to perform "name" sort by
        :return: Sorted data
        """
        def _sort_key(item):
            value_sort_key = item[ChartSortBy.value.name]
            name_sort_key = str(item[name_key or ChartSortBy.name.name]).upper()
            if self.sort.sort_by == ChartSortBy.value:
                return (value_sort_key, name_sort_key)
            if self.sort.sort_by == ChartSortBy.name:
                return (name_sort_key, value_sort_key)
            raise NotImplementedError

        return sorted(data, key=_sort_key, reverse=self.sort.sort_order == ChartSortOrder.desc)
