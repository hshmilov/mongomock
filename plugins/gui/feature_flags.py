import logging

from axonius.mixins.configurable import Configurable

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=useless-super-delegation
class FeatureFlags(Configurable):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    # pylint: disable=R0201
    def _on_config_update(self, config):
        logger.info(f'Loading FeatureFlags config: {config}')

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'trial_end',
                    'title': 'Date for Trial to End',
                    'type': 'string',
                    'format': 'date-time'
                },
                {
                    'name': 'locked_actions',
                    'title': 'Actions Locked for Client',
                    'type': 'array',
                    'items': {
                        'type': 'string',
                        'enum': []
                    }
                }
            ],
            'required': ['is_trial'],
            'name': 'feature_flags',
            'title': 'Feature Flags',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'trial_end': None,
            'locked_actions': [
                'cybereason_isolate',
                'cybereason_unisolate',
                'carbonblack_defense_change_policy',
                'tenable_sc_add_ips_to_asset'
            ]
        }
