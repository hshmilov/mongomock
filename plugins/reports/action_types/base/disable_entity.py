import logging

from funcy import chunks

from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME
from axonius.entities import EntityType
from reports.action_types.action_type_base import ActionTypeBase
from reports.enforcement_classes import EntitiesResult, EntityResult

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=W0212


class DisableEntities(ActionTypeBase):
    """
    Uses disabelable to disable entities
    """

    @staticmethod
    def config_schema() -> dict:
        return {
        }

    @staticmethod
    def default_config() -> dict:
        return {
        }

    def _run(self) -> EntitiesResult:
        feature_name, urlpath = {
            EntityType.Devices: ('Devicedisabelable', 'devices/disable'),
            EntityType.Users: ('Userdisabelable', 'users/disable')
        }[self._entity_type]
        relevant_plugin_unique_names = list(self._plugin_base._adapters_with_feature(feature_name))

        for plugin_unique_name in relevant_plugin_unique_names:
            for chunk in chunks(10000, self._internal_axon_ids):
                db_cursor = self.entity_db.find({
                    'internal_axon_id': {
                        '$in': chunk
                    },
                    f'adapters.{PLUGIN_UNIQUE_NAME}': plugin_unique_name
                }, projection={
                    'adapters.$': 1,
                })
                entities = [x['adapters'][0]['data']['id']
                            for x
                            in db_cursor]
                if not entities:
                    continue

                response = self._plugin_base.request_remote_plugin(urlpath, plugin_unique_name, method='POST',
                                                                   json=entities)
                if response.status_code != 200:
                    logger.error(f'Error on disabling on {plugin_unique_name}: {response.content}')
                    yield from (EntityResult(id_, False, response.content) for id_ in chunk)
                else:
                    yield from (EntityResult(id_, True, 'Disabled entity') for id_ in chunk)
