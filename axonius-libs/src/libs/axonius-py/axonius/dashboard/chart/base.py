import logging
from enum import Enum, auto

from dataclasses import dataclass
from dataclasses_json import DataClassJsonMixin

from axonius.dashboard.chart.config import ChartConfig
from axonius.dashboard.chart.compare import CompareConfig
from axonius.dashboard.chart.intersect import IntersectConfig
from axonius.dashboard.chart.matrix import MatrixConfig
from axonius.dashboard.chart.segment import SegmentConfig
from axonius.dashboard.chart.segment_adapter import SegmentAdapterConfig
from axonius.dashboard.chart.abstract import AbstractConfig
from axonius.dashboard.chart.timeline import TimelineConfig
from axonius.dashboard.chart.timeline_segment import TimelineSegmentConfig
from axonius.modules.common import AxoniusCommon

logger = logging.getLogger(f'axonius.{__name__}')


class ChartMetric(Enum):
    """
    Possible scales of data to represent using a chart
    """
    intersect = auto()
    compare = auto()
    segment = auto()
    adapter_segment = auto()
    segment_timeline = auto()
    abstract = auto()
    timeline = auto()
    matrix = auto()


class ChartView(Enum):
    """
    Possible representations for charts
    """
    histogram = auto()
    adapter_histogram = auto()
    pie = auto()
    summary = auto()
    line = auto()
    stacked = auto()


@dataclass
class Chart(DataClassJsonMixin):
    """
    An Axonius chart has the following common properties, where "config" varies according to the "metric".

    In order to implement a new type of chart:
    - Add the type to "ChartMetric" enum
    - Inherit the "ChartConfig" with needed properties and "generate_data" using them
    - Declare the "metric" and the new config in the following "from_dict" method
    """

    name: str

    metric: ChartMetric

    view: ChartView

    config: ChartConfig

    @staticmethod
    def from_dict(data: dict):
        metric_to_config_type = {
            ChartMetric.intersect: IntersectConfig,
            ChartMetric.compare: CompareConfig,
            ChartMetric.segment: SegmentConfig,
            ChartMetric.adapter_segment: SegmentAdapterConfig,
            ChartMetric.abstract: AbstractConfig,
            ChartMetric.timeline: TimelineConfig,
            ChartMetric.segment_timeline: TimelineSegmentConfig,
            ChartMetric.matrix: MatrixConfig
        }
        metric = ChartMetric[data['metric']]
        return Chart(name=data['name'],
                     metric=metric,
                     view=ChartView[data['view']],
                     config=metric_to_config_type[metric].from_dict(data['config']))

    @staticmethod
    def generate_from_id(chart_id: str, common: AxoniusCommon, date: str = None):
        chart_obj = Chart.from_dict(common.data.find_chart(chart_id))
        return chart_obj.generate_data(common, date)

    def generate_data(self, common: AxoniusCommon, for_date: str = None):
        try:
            return self.config.generate_data(common, for_date)
        except Exception:
            logger.exception(f'Error generating chart {self.name}')
            return []
