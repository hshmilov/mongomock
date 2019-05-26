from axonius.correlator_base import CorrelatorBase
from axonius.entities import EntityType
from axonius.utils.files import get_local_config_file
from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME


from static_users_correlator.engine import StaticUserCorrelatorEngine


class StaticUsersCorrelatorService(CorrelatorBase):
    def __init__(self, *args, **kwargs):
        super().__init__(get_local_config_file(__file__), *args, **kwargs)

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
        return list(self.users_db.aggregate([
            {'$match': match},
            {'$project': {
                'internal_axon_id': 1,
                'adapters': {
                    '$map': {
                        'input': '$adapters',
                        'as': 'adapter',
                        'in': {
                            'plugin_name': '$$adapter.plugin_name',
                            PLUGIN_UNIQUE_NAME: '$$adapter.plugin_unique_name',
                            'data': {
                                'id': '$$adapter.data.id',
                                'ad_user_principal_name': '$$adapter.data.ad_user_principal_name',
                                'username': '$$adapter.data.username',
                                'ad_display_name': '$$adapter.data.ad_display_name',
                                'mail': '$$adapter.data.mail',
                                'domain': '$$adapter.data.domain',

                            }
                        }
                    }
                },
                'tags': 1
            }}
        ]))
