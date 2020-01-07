import logging
from datetime import datetime, timedelta

from axonius.consts.gui_consts import FeatureFlagsNames, RootMasterNames
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
                    'name': FeatureFlagsNames.TrialEnd,
                    'title': 'Date for Trial to End',
                    'type': 'string',
                    'format': 'date-time'
                },
                {
                    'name': FeatureFlagsNames.LockedActions,
                    'title': 'Actions Locked for Client',
                    'type': 'array',
                    'items': {
                        'type': 'string',
                        'enum': []
                    }
                },
                {
                    'name': RootMasterNames.root_key,
                    'title': 'Root Master Settings',
                    'type': 'array',
                    'items': [
                        {
                            'name': RootMasterNames.enabled,
                            'title': 'Enable Root Master Mode',
                            'type': 'bool',
                        },
                        {
                            'name': RootMasterNames.delete_backups,
                            'title': 'Delete backups from S3 after parse',
                            'type': 'bool'
                        }
                    ],
                    'required': [
                        'enabled', RootMasterNames.delete_backups
                    ],
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
            FeatureFlagsNames.TrialEnd: (datetime.now() + timedelta(days=30)).isoformat()[:10].replace('-', '/'),
            FeatureFlagsNames.LockedActions: [],
            RootMasterNames.root_key: {
                RootMasterNames.enabled: False,
                RootMasterNames.delete_backups: False,
            }
        }
