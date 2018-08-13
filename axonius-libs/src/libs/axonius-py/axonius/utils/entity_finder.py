import logging
from typing import Tuple

from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME

logger = logging.getLogger(f'axonius.{__name__}')


class EntityFinder(object):
    """
    Fetch given entities using their ID
    """

    def __init__(self, entity_db, clients, plugin_unique_name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__entity_db = entity_db
        self.__clients = clients
        self.__plugin_unique_name = plugin_unique_name

    def __find_entity_in_db(self, entity_id):
        """
        Find the entity using the aggregator DB
        """
        entity = self.__entity_db.find_one({'adapters':
                                            {"$elemMatch": {
                                                "data.id": entity_id,
                                                PLUGIN_UNIQUE_NAME: self.__plugin_unique_name
                                            }}
                                            })
        if entity is None:
            logger.error(f"Can't find entity for {entity_id}")
            return None

        data = next((data for data in entity['adapters'] if data[PLUGIN_UNIQUE_NAME] == self.__plugin_unique_name),
                    None)
        assert data, "Can't find adapter that we looked for in $elemMatch"

        return data

    def get_data_and_client_data(self, entity_id) -> Tuple[dict, object]:
        """
        Fetches
        the data given by this adapter for the given entity
        the client data used to fetch this entity
        :param entity_id:
        """
        entity = self.__find_entity_in_db(entity_id)
        if not entity:
            raise Exception(f"Can't find entity {entity_id}")
        client = self.__clients.get(entity['client_used'])
        if not client:
            raise Exception(f"Client used to fetch this entity ({client}) is unavailable")
        return entity['data'], client
