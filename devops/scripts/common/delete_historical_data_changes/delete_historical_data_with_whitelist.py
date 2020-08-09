"""
Gets a date as an input and deletes all historical data before that date.
"""
import sys

from datetime import timezone
import dateutil.parser

from axonius.entities import EntityType
from services.axonius_service import AxoniusService


def main():
    blacklist = """
2020-07-21 04:10:26.704000
2020-06-28 11:26:12.933000
2020-05-31 01:10:12.891000
2020-04-30 09:08:47.551000
2020-03-31 19:45:43.496000
2020-02-17 17:33:38.305000
2020-01-31 09:37:35.828000
2019-12-31 11:16:49.059000
    """.strip().splitlines()

    ax = AxoniusService()

    query_for_dates_that_we_delete = {
        'accurate_for_datetime': {'$nin': [dateutil.parser.parse(x) for x in blacklist]}
    }
    query_for_dates_that_we_keep = {
        'accurate_for_datetime': {'$in': [dateutil.parser.parse(x) for x in blacklist]}
    }

    all_historical_dates_to_delete = ax.db.get_historical_entity_db_view(EntityType.Devices).distinct(
        'accurate_for_datetime', query_for_dates_that_we_delete
    )

    historical_dates_str = '\n'.join(sorted([str(x) for x in all_historical_dates_to_delete]))
    print(f'Devices: Found The following dates: \n{historical_dates_str}')

    all_historical_dates_to_keep = ax.db.get_historical_entity_db_view(EntityType.Devices).distinct(
        'accurate_for_datetime', query_for_dates_that_we_keep
    )
    historical_dates_str = ', '.join(sorted([str(x) for x in all_historical_dates_to_keep]))
    print(f'Keeping: \n{historical_dates_str}')

    answer = input(f'Should proceed to deletion? [y/n]: ')

    if answer != 'y':
        print(f'Exiting...')
        return -1

    for entity_type in EntityType:
        db = ax.db.get_historical_entity_db_view(entity_type)
        db_raw = ax.db.get_historical_raw_entity_db_view(entity_type)

        print(f'Deleting parsed {entity_type}...')
        db.delete_many(query_for_dates_that_we_delete)
        print(f'Deleting raw {entity_type}...')
        db_raw.delete_many(query_for_dates_that_we_delete)

    print(f'Done')
    return 0


if __name__ == '__main__':
    sys.exit(main())
