from datetime import date, datetime
from typing import Iterable, Tuple, List
from dataclasses import dataclass

from axonius.dashboard.chart.segment import SegmentConfig
from axonius.dashboard.chart.timeline import AbstractTimelineConfig
from axonius.modules.common import AxoniusCommon


@dataclass
class TimelineSegmentConfig(AbstractTimelineConfig):

    segment_config: SegmentConfig

    @staticmethod
    def from_dict(data: dict):
        data['sort'] = {
            'sort_by': 'value', 'sort_order': 'desc'
        }
        return TimelineSegmentConfig(timeframe=data['timeframe'],
                                     segment_config=SegmentConfig.from_dict(data))

    def calculate_lines(self, common: AxoniusCommon, date_ranges: Iterable[Tuple[date, date]]) -> List:
        field_path_partition = self.segment_config.field_name.rpartition('.')
        field_parent = field_path_partition[0] or ''
        field_name = field_path_partition[2]
        reduced_filters = self.segment_config.get_reduced_filters(field_name)

        def date_handler(common: AxoniusCommon, for_date: datetime):
            base_view, aggregate_results = self.segment_config.query_chart_segment_results(
                common, field_parent, for_date.date().isoformat(), [*reduced_filters])
            if not base_view or not aggregate_results:
                return None

            # go over segmentation results
            counted_results = self.segment_config.get_counted_results(aggregate_results, reduced_filters)
            total_count = 0
            num_of_segments = 0
            for result_name, result_count in counted_results.items():
                if result_name == 'No Value' and (not self.segment_config.include_empty
                                                  or ''.join(reduced_filters[field_name])):
                    continue
                num_of_segments += 1
                total_count += result_count
            return (num_of_segments, total_count)

        points = self.fetch_timeline_points(common, self.segment_config.entity, date_ranges, date_handler)
        lines = [{'title': 'Segment count', 'points': {}}, {'title': 'Total segment values', 'points': {}}]
        for point_date, point_counters in points.items():
            for i, counter in enumerate(point_counters):
                lines[i]['points'][point_date] = counter
        return lines
