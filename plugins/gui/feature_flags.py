import logging

from axonius.mixins.configurable import Configurable

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=useless-super-delegation
class FeatureFlags(Configurable):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _on_config_update(self, config):
        logger.info(f'Loading FeatureFlags config: {config}')

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'is_trial',
                    'title': 'Is trial mode',
                    'type': 'bool'
                },
                {
                    'name': 'is_full_ec',
                    'title': 'Is full EC allowed',
                    'type': 'bool'
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
            'is_poc': False,
            'is_full_ec': False
        }
