"""
Gets a date as an input and deletes all historical data before that date.
"""
import sys

from datetime import timezone
import dateutil.parser

from axonius.entities import EntityType
from services.axonius_service import AxoniusService


def main():
    try:
        date = dateutil.parser.parse(sys.argv[1]).astimezone(timezone.utc)

        answer = input(f'Got this date: {date} (GMT).\nIs this the correct date? [y/n]: ')
        if answer != 'y':
            print(f'Exiting...')
            return -1
    except Exception:
        print(f'Usage: {sys.argv[0]} [date] [min_date].\ne.g. {sys.argv[0]} "Jan 27 2019 00:00:00"')
        return -1

    try:
        min_date = dateutil.parser.parse(sys.argv[2]).astimezone(timezone.utc)

        answer = input(f'Got this date: {min_date} (GMT).\nIs this the correct date? [y/n]: ')
        if answer != 'y':
            print(f'Exiting...')
            return -1
    except Exception:
        min_date = None

    ax = AxoniusService()

    if min_date:
        print(f'Building query with max {date} and min {min_date}')
        query = {'accurate_for_datetime': {'$lt': date, '$gt': min_date}}
    else:
        print(f'Building query with max {date} and no min date')
        query = {'accurate_for_datetime': {'$lt': date}}

    all_historical_dates = ax.db.get_historical_entity_db_view(EntityType.Devices).distinct(
        'accurate_for_datetime', query
    )

    answer = input(f'Devices: Found The following dates: {",".join([str(x) for x in all_historical_dates])}\n'
                   f'Should proceed to deletion? [y/n]: ')

    if answer != 'y':
        print(f'Exiting...')
        return -1

    for entity_type in EntityType:
        db = ax.db.get_historical_entity_db_view(entity_type)
        db_raw = ax.db.get_historical_raw_entity_db_view(entity_type)

        print(f'Deleting parsed {entity_type}...')
        db.delete_many(query)
        print(f'Deleting raw {entity_type}...')
        db_raw.delete_many(query)

    print(f'Done')
    return 0


if __name__ == '__main__':
    sys.exit(main())
