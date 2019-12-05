#!/usr/bin/env python3
from services.axonius_service import AxoniusService
from random import randint
from datetime import datetime, timedelta
import sys


def main():
    ax = AxoniusService()
    entity_type = sys.argv[1] if len(sys.argv) > 1 else 'devices'
    history_db = ax.db.client['aggregator'][f'historical_{entity_type}_db_view']
    entity_count = ax.db.client['aggregator'][f'{entity_type}_db'].count_documents({})
    for day in range(1, 60):
        try:
            entities_limit = randint(entity_count - 8, entity_count)
            entities_skip = randint(0, entity_count - entities_limit)
            entities = list(history_db.find().skip(entities_skip).limit(entities_limit))
            new_date = datetime.now() - timedelta(day)
            for entity in entities:
                del entity['_id']
                entity['accurate_for_datetime'] = new_date
            history_db.insert_many(entities)

        except Exception as e:
            print(f'Failed to set for {day}: {e}')


if __name__ == '__main__':
    main()
