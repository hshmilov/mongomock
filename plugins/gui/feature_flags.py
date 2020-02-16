import logging
from datetime import datetime, timedelta

from axonius.consts.gui_consts import FeatureFlagsNames, RootMasterNames, CloudComplianceNames
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
                    'name': FeatureFlagsNames.ReenterCredentials,
                    'title': 'Reenter credentials on adapter connection update',
                    'type': 'bool'
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
                    'name': FeatureFlagsNames.CloudCompliance,
                    'title': 'Cloud Asset Compliance Center',
                    'type': 'array',
                    'items': [
                        {
                            'name': CloudComplianceNames.Visible,
                            'title': 'Cloud Visible',
                            'type': 'bool'
                        },
                        {
                            'name': CloudComplianceNames.Enabled,
                            'title': 'Cloud Enabled',
                            'type': 'bool',
                        },
                    ],
                    'required': [
                        CloudComplianceNames.Visible, CloudComplianceNames.Enabled
                    ],
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
            FeatureFlagsNames.CloudCompliance: {
                CloudComplianceNames.Visible: False,
                CloudComplianceNames.Enabled: False,
            },
            RootMasterNames.root_key: {
                RootMasterNames.enabled: False,
                RootMasterNames.delete_backups: False,
            },
            FeatureFlagsNames.ReenterCredentials: False
        }
