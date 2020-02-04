"""
Gets a date as an input and deletes all historical data before that date.
"""
import sys

import dateutil.parser
from datetime import timezone

from axonius.entities import EntityType
from services.axonius_service import AxoniusService


def main():
    try:
        _, date = sys.argv
    except Exception:
        print(f'Usage: {sys.argv[0]} [date].\ne.g. {sys.argv[0]} "Jan 27 2019 00:00:00"')
        return -1

    date = dateutil.parser.parse(date).astimezone(timezone.utc)

    answer = input(f'Got this date: {date} (GMT).\nIs this the correct date? [y/n]: ')
    if answer != 'y':
        print(f'Exiting...')
        return -1

    ax = AxoniusService()

    for entity_type in EntityType:
        db = ax.db.get_historical_entity_db_view(entity_type)
        db_raw = ax.db.get_historical_raw_entity_db_view(entity_type)

        query = {'accurate_for_datetime': {'$lt': date}}
        count = db.count(query)
        count_raw = db_raw.count(query)

        answer = input(f'{entity_type}: Found {count} devices with {count_raw} device-adapters.\n'
                       f'Should proceed to deletion? [y/n]: ')
        if answer != 'y':
            print(f'Exiting...')
            return -1

        db.delete_many(query)
        db_raw.delete_many(query)

    print(f'Done')
    return 0


if __name__ == '__main__':
    sys.exit(main())
