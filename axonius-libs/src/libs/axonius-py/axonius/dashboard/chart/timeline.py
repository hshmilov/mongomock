import logging
from abc import abstractmethod
from datetime import timedelta, datetime, date
from enum import Enum, auto
from multiprocessing import cpu_count
from typing import List, Iterable, Tuple, Callable

from dataclasses import dataclass

from axonius.dashboard.chart.config import ChartConfig
from axonius.entities import EntityType
from axonius.modules.common import AxoniusCommon
from axonius.utils.datetime import parse_date
from axonius.utils.threading import GLOBAL_RUN_AND_FORGET

logger = logging.getLogger(f'axonius.{__name__}')


class TimelineRangeType(Enum):
    """
    Possible types of a timeframe range for the timeline chart
    """
    absolute = auto()
    relative = auto()


class TimelineRangeUnit(Enum):
    """
    Possible units for defining a relative timeframe
    """
    day = 1
    week = 7
    month = 30
    year = 365


@dataclass
class AbstractTimelineConfig(ChartConfig):

    timeframe: dict

    def generate_data(self, common: AxoniusCommon, for_date: str):
        date_from, date_to = self.parse_ranges()
        if not date_from or not date_to:
            return None

        date_ranges = list(self.get_date_ranges(date_from, date_to))
        lines = self.calculate_lines(common, date_ranges)
        return self.format_lines(date_from, date_to, lines)

    def parse_ranges(self):
        """
        Timeframe dict includes choice of range for the timeline chart.
        It can be absolute and include a date to start and to end the series,
        or relative and include a unit and count to fetch back from moment of request.
        """
        try:
            range_type = TimelineRangeType[self.timeframe['type']]
        except KeyError:
            logger.error(f'Unexpected timeframe type {self.timeframe["type"]}')
            return None, None
        if range_type == TimelineRangeType.absolute:
            logger.info(f'Gathering data between {self.timeframe["from"]} and {self.timeframe["to"]}')
            try:
                date_to = parse_date(self.timeframe['to'])
                date_from = parse_date(self.timeframe['from'])
            except ValueError:
                logger.exception('Given date to or from is invalid')
                return None, None
        else:
            logger.info(f'Gathering data from {self.timeframe["count"]} {self.timeframe["unit"]} back')
            date_to = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            try:
                range_unit = TimelineRangeUnit[self.timeframe['unit']]
            except KeyError:
                logger.error(f'Unexpected timeframe unit {self.timeframe["unit"]} for reltaive chart')
                return None, None
            date_from = date_to - timedelta(days=self.timeframe['count'] * range_unit.value)
        return date_from.replace(tzinfo=None), date_to.replace(tzinfo=None)

    @staticmethod
    def get_date_ranges(date_from: datetime, date_to: datetime) -> Iterable[Tuple[date, date]]:
        """
        Generate date intervals from the given datetimes according to the amount of threads
        """
        date_from = date_from.date()
        date_to = date_to.date()

        thread_count = min([cpu_count(), (date_to - date_from).days]) or 1
        interval = (date_to - date_from) / thread_count

        for i in range(thread_count):
            date_from = date_from + (interval * i)
            date_to = date_from + (interval * (i + 1))
            yield (date_from, date_to)

    @abstractmethod
    def calculate_lines(self, common: AxoniusCommon, date_ranges: Iterable[Tuple[date, date]]) -> List:
        pass

    @staticmethod
    def fetch_timeline_points(common: AxoniusCommon, entity_type: EntityType,
                              date_ranges: Iterable[Tuple[date, date]], date_handler: Callable):

        def aggregate_for_date_range(args):
            range_from, range_to = args
            historical_collection = common.data.entity_history_collection[entity_type]
            historical_in_range = historical_collection.aggregate([{
                '$project': {
                    'accurate_for_datetime': 1
                }
            }, {
                '$match': {
                    'accurate_for_datetime': {
                        '$lte': datetime.combine(range_to, datetime.min.time()),
                        '$gte': datetime.combine(range_from, datetime.min.time()),
                    }
                }
            }, {
                '$group': {
                    '_id': '$accurate_for_datetime'
                }
            }])

            historical_counts = {}
            for historical_group in historical_in_range:
                historical_counts[historical_group['_id']] = date_handler(common, historical_group['_id'])
            return historical_counts

        points = {}
        for results in list(GLOBAL_RUN_AND_FORGET.map(aggregate_for_date_range, date_ranges)):
            for accurate_for_datetime, count in results.items():
                points[accurate_for_datetime.strftime('%m/%d/%Y')] = count
        return points

    @staticmethod
    def format_lines(date_from, date_to, lines):
        if not lines or not lines[0]['points'].keys():
            return None
        # find the first date with value, before which data is not relevant
        first_date_with_value = datetime.strptime(min([min(line_group['points'].keys()) for line_group in lines]),
                                                  '%m/%d/%Y')
        # fix the from_date for not having undefined values before the first day we have values
        if date_from < first_date_with_value:
            date_from = first_date_with_value

        scale = [(date_from + timedelta(i)) for i in range((date_to - date_from).days + 1)]
        return [
            ['Day'] + [{
                'label': line['title'],
                'type': 'number'
            } for line in lines],
            *[[day] + [line['points'].get(day.strftime('%m/%d/%Y')) for line in lines] for day in scale]
        ]


@dataclass
class TimelineConfig(AbstractTimelineConfig):

    views: List[dict]

    intersection: bool

    @staticmethod
    def from_dict(data: dict):
        return TimelineConfig(timeframe=data['timeframe'],
                              views=data['views'],
                              intersection=bool(data['intersection']))

    def calculate_lines(self, common: AxoniusCommon, date_ranges: Iterable[Tuple[date, date]]) -> List:
        if self.intersection:
            return list(self.intersect_lines(common, date_ranges))
        return list(self.compare_lines(common, date_ranges))

    @staticmethod
    def date_handler_generator(match_filter: str, entity_type: EntityType):
        def date_handler(common: AxoniusCommon, for_date: datetime):
            collection, date_query = common.data.entity_collection_query_for_date(
                entity_type, for_date.strftime('%Y-%m-%d'))
            base_filter = common.query.parse_aql_filter(match_filter, for_date, entity_type)
            if date_query:
                base_filter = {
                    '$and': [base_filter, date_query]
                }
            return common.query.count_matches(collection, base_filter)

        return date_handler

    def intersect_lines(self, common: AxoniusCommon, date_ranges: Iterable[Tuple[date, date]]) -> Iterable[dict]:
        if len(self.views) != 2 or not self.views[0].get('id'):
            logger.error(f'Unexpected number of views for performing intersection {len(self.views)}')
            return
        first_entity_type = EntityType(self.views[0]['entity'])
        second_entity_type = EntityType(self.views[1]['entity'])

        # first query handling
        base_from_db = common.data.find_view(first_entity_type, self.views[0]['id'])
        if not base_from_db or not base_from_db.get('view', {}).get('query'):
            return
        base_filter = base_from_db['view']['query']['filter']
        yield {
            'title': base_from_db['name'],
            'points': self.fetch_timeline_points(common, first_entity_type, date_ranges, self.date_handler_generator(
                base_filter, first_entity_type))
        }
        # second query handling
        intersecting_from_db = common.data.find_view(second_entity_type, self.views[1]['id'])
        if not intersecting_from_db or not intersecting_from_db.get('view', {}).get('query'):
            return
        intersecting_filter = intersecting_from_db['view']['query']['filter']
        if base_filter:
            intersecting_filter = f'({base_filter}) and {intersecting_filter}'
        yield {
            'title': f'{base_from_db["name"]} and {intersecting_from_db["name"]}',
            'points': self.fetch_timeline_points(common, second_entity_type, date_ranges, self.date_handler_generator(
                intersecting_filter, second_entity_type))
        }

    def compare_lines(self, common: AxoniusCommon, date_ranges: Iterable[Tuple[date, date]]) -> Iterable[dict]:
        for view in self.views:
            if not view.get('id'):
                continue
            entity = EntityType(view['entity'])
            base_from_db = common.data.find_view(entity, view['id'])
            base_view = base_from_db['view']
            if not base_view or not base_view.get('query'):
                return
            yield {
                'title': base_from_db['name'],
                'points': self.fetch_timeline_points(common, entity, date_ranges, self.date_handler_generator(
                    base_view['query']['filter'], entity))
            }
