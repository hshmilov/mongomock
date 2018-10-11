from services.axonius_service import AxoniusService
from random import randint
from datetime import datetime, timedelta
import sys


def main():
    ax = AxoniusService()
    entity_type = sys.argv[1] if len(sys.argv) > 1 else 'devices'
    history_db = ax.db.client['aggregator'][f'historical_{entity_type}_db_view']
    previous_entities_number = 0
    for day in range(60):
        try:
            entities_number = randint(1, 100)
            entities = list(history_db.find().skip(previous_entities_number).limit(entities_number))
            previous_entities_number = entities_number
            for entity in entities:
                del entity['_id']
                entity['accurate_for_datetime'] = datetime.now() - timedelta(day)
            history_db.insert_many(entities)

        except Exception as e:
            print(f'Failed to set for {day}: {e}')


if __name__ == '__main__':
    main()
