from axonius.correlator_base import CorrelatorBase
from axonius.entities import EntityType
from axonius.utils.files import get_local_config_file
from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME, STATIC_USERS_CORRELATOR_PLUGIN_NAME

from static_users_correlator.engine import StaticUserCorrelatorEngine


class StaticUsersCorrelatorService(CorrelatorBase):
    def __init__(self, *args, **kwargs):
        super().__init__(get_local_config_file(__file__),
                         requested_unique_plugin_name=STATIC_USERS_CORRELATOR_PLUGIN_NAME, *args, **kwargs)

        self._correlation_engine = StaticUserCorrelatorEngine()

    def _correlate(self, entities: list):
        return self._correlation_engine.correlate(entities,
                                                  correlation_config={
                                                      'email_prefix_correlation': self._email_prefix_correlation})

    @property
    def _entity_to_correlate(self) -> EntityType:
        return EntityType.Users

    def get_entities_from_ids(self, entities_ids=None):
        if entities_ids is None:
            match = {}
        else:
            match = {
                'internal_axon_id': {
                    '$in': entities_ids
                }
            }
        fields_to_get = ('id', 'ad_user_principal_name', 'username', 'ad_display_name', 'mail', 'domain',
                         'associated_adapter_plugin_name', 'value', 'type', 'name')
        projection = {
            f'adapters.data.{field}': True for field in fields_to_get
        }
        projection.update({
            f'tags.data.{field}': True for field in fields_to_get
        })

        return list(self.users_db.find(match, projection={
            'internal_axon_id': True,
            'adapters.plugin_name': True,
            f'adapters.{PLUGIN_UNIQUE_NAME}': True,
            'tags.plugin_name': True,
            f'tags.{PLUGIN_UNIQUE_NAME}': True,
            'tags.associated_adapters': True,
            'tags.name': True,
            **projection
        }))
