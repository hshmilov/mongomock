import logging
from datetime import datetime, timedelta

from axonius.consts.gui_consts import FeatureFlagsNames, RootMasterNames, CloudComplianceNames, ParallelSearch
from axonius.consts.plugin_consts import INSTANCE_CONTROL_PLUGIN_NAME
from axonius.mixins.configurable import Configurable
from axonius.utils.build_modes import get_build_mode, BuildModes

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=useless-super-delegation, no-member
class FeatureFlags(Configurable):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    # pylint: disable=R0201,E0203,no-member
    def _on_config_update(self, config):
        if config == self._current_feature_flag_config:
            return

        if config.get(FeatureFlagsNames.Bandicoot, False) != \
                self._current_feature_flag_config.get(FeatureFlagsNames.Bandicoot, False):
            if config[FeatureFlagsNames.Bandicoot]:
                self.start_bandicoot()
            else:
                self.stop_bandicoot()
        # In order for core to update all plugins with the new settings (specially fips)
        logger.info(f'Loading FeatureFlags config: {config}')
        # this variable is set in PluginBase
        self._current_feature_flag_config = self.feature_flags_config()
        resp = self.request_remote_plugin('update_config', 'core', method='POST')
        if resp.status_code == 200:
            logger.info('Feature Flags settings updated in all plugins')
        else:
            logger.error(f'An error occurred while trying to update all feature flags config: {resp.content}')

    def start_bandicoot(self):
        logger.info('Starting bandicoot')
        try:
            self._trigger_remote_plugin(INSTANCE_CONTROL_PLUGIN_NAME, f'start:postgres', reschedulable=False,
                                        blocking=True, error_as_warning=True)
            self._trigger_remote_plugin(INSTANCE_CONTROL_PLUGIN_NAME, f'start:bandicoot', reschedulable=False,
                                        blocking=False, error_as_warning=True)
        # catch any exception, otherwise gui will crash, any error that is raised it already documented in the
        # trigger functions
        except BaseException:
            pass

    def stop_bandicoot(self):
        logger.info('Stopping bandicoot')
        try:
            self._trigger_remote_plugin(INSTANCE_CONTROL_PLUGIN_NAME, f'stop:bandicoot', reschedulable=False,
                                        blocking=False, error_as_warning=True)
            self._trigger_remote_plugin(INSTANCE_CONTROL_PLUGIN_NAME, f'stop:postgres', reschedulable=False,
                                        blocking=False, error_as_warning=True)
        # see start bandicoot function
        except BaseException:
            pass

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
                    'name': FeatureFlagsNames.QueryTimelineRange,
                    'title': 'Enable unlimited query timeline range',
                    'type': 'bool'
                },
                {
                    'name': FeatureFlagsNames.RefetchAssetEntityAction,
                    'title': 'Allow Refetch Asset Entity Action',
                    'type': 'bool'
                },
                {
                    'name': FeatureFlagsNames.EnableFIPS,
                    'title': 'Enable FIPS on MongoEncrypt actions',
                    'type': 'bool'
                },
                {
                    'name': FeatureFlagsNames.EnableSaaS,
                    'title': 'Enable Tunnel',
                    'type': 'bool'
                },
                {
                    'name': FeatureFlagsNames.DoNotUseSoftwareNameAndVersionField,
                    'title': 'Do not populate software "name and version" field',
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
                    'name': FeatureFlagsNames.Bandicoot,
                    'title': 'Run Bandicoot container (results will be available next cycle)',
                    'type': 'bool',
                },
                {
                    'name': FeatureFlagsNames.ExperimentalAPI,
                    'title': 'Enable search via Postgres (you need to run Bandicoot container first)',
                    'type': 'bool',
                },
                {
                    'name': FeatureFlagsNames.BandicootCompare,
                    'title': 'Enable compare query results with Bandicoot, will not work '
                             'with experimental API turned on',
                    'type': 'bool',
                },
                {
                    'name': FeatureFlagsNames.ExpiryDate,
                    'title': 'Contract Expiry Date',
                    'type': 'string',
                    'format': 'date-time'
                },
                {
                    'name': FeatureFlagsNames.LockOnExpiry,
                    'title': 'Lock on contract expiry',
                    'type': 'bool'
                },
                {
                    'name': FeatureFlagsNames.EnforcementCenter,
                    'title': 'Enable Enforcement Center',
                    'type': 'bool',
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
                        {
                            'name': CloudComplianceNames.ExpiryDate,
                            'title': 'Cloud Trial Expiration Date',
                            'type': 'string',
                            'format': 'date-time',
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
                            'name': RootMasterNames.SMB_enabled,
                            'title': 'Enable Root Master Mode (SMB)',
                            'type': 'bool',
                        },
                        {
                            'name': RootMasterNames.delete_backups,
                            'title': 'Delete Backups After Parse',
                            'type': 'bool',
                        },
                    ],
                    'required': [
                        RootMasterNames.enabled,
                        RootMasterNames.SMB_enabled,
                        RootMasterNames.delete_backups,
                    ],
                },
                {
                    'name': ParallelSearch.root_key,
                    'title': 'Parallel Adapters Search',
                    'type': 'array',
                    'items': [
                        {
                            'name': ParallelSearch.enabled,
                            'title': 'Enabled',
                            'type': 'bool'
                        }
                    ],
                    'required': [
                        ParallelSearch.enabled
                    ],
                }
            ],
            'required': ['is_trial', FeatureFlagsNames.ExperimentalAPI,  FeatureFlagsNames.LockOnExpiry,
                         FeatureFlagsNames.QueryTimelineRange, FeatureFlagsNames.EnforcementCenter],
            'name': 'feature_flags',
            'title': 'Feature Flags',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            FeatureFlagsNames.TrialEnd: (datetime.now() + timedelta(days=30)).isoformat()[:10].replace('-', '/'),
            FeatureFlagsNames.ExpiryDate: '',
            FeatureFlagsNames.LockOnExpiry: False,
            FeatureFlagsNames.LockedActions: [],
            FeatureFlagsNames.Bandicoot: False,
            FeatureFlagsNames.ExperimentalAPI: False,
            FeatureFlagsNames.CloudCompliance: {
                CloudComplianceNames.Visible: False,
                CloudComplianceNames.Enabled: False,
                CloudComplianceNames.ExpiryDate: '',
            },
            RootMasterNames.root_key: {
                RootMasterNames.enabled: False,
                RootMasterNames.SMB_enabled: False,
                RootMasterNames.delete_backups: False,
            },
            ParallelSearch.root_key: {
                ParallelSearch.enabled: False
            },
            FeatureFlagsNames.ReenterCredentials: False,
            FeatureFlagsNames.RefetchAssetEntityAction: False,
            FeatureFlagsNames.EnableFIPS: get_build_mode() == BuildModes.fed.value,
            FeatureFlagsNames.EnableSaaS: False,
            FeatureFlagsNames.QueryTimelineRange: False,
            FeatureFlagsNames.EnforcementCenter: True,
            FeatureFlagsNames.DoNotUseSoftwareNameAndVersionField: False,
        }
