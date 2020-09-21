import logging
import pickle
from typing import List

from axonius.clients.cisco.abstract import AbstractCiscoClient

logger = logging.getLogger(f'axonius.{__name__}')


def query_devices_by_client_cisco(cisco_client: AbstractCiscoClient):
    did_throw_critical = False
    with cisco_client:
        for entity in cisco_client.query_all():
            try:
                yield pickle.dumps(entity)
            except Exception:
                if not did_throw_critical:
                    # flood-protection. we do not want thousands of criticals.
                    logger.critical(f'Could not yield from cisco adapter', exc_info=True)
                    did_throw_critical = True


def prepare_for_parse_raw_data_cisco(entities: List[bytes]):
    try:
        for entity in entities:
            yield pickle.loads(entity)
    except Exception:
        logger.critical(f'Could not load pickable object in cisco', exc_info=True)
        raise
