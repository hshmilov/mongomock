import logging

from axonius.clients.qualys import consts
from axonius.clients.qualys.connection import QualysScansConnection
from axonius.types.enforcement_classes import EntitiesResult, EntityResult
from reports.action_types.action_type_base import ActionTypeBase, generic_fail
from reports.action_types.base.ips_scans_utils import get_ips_from_view_as_iter

logger = logging.getLogger(f'axonius.{__name__}')

ADAPTER_NAME = 'qualys_adapter'


class QualysCreateAsset(ActionTypeBase):
    @staticmethod
    def config_schema() -> dict:
        schema = {
            'items': [
                {'name': consts.QUALYS_SCANS_DOMAIN, 'title': 'Qualys Cloud Platform domain', 'type': 'string'},
                {'name': consts.USERNAME, 'title': 'User name', 'type': 'string'},
                {'name': consts.PASSWORD, 'title': 'Password', 'type': 'string', 'format': 'password'},
                {'name': consts.VERIFY_SSL, 'title': 'Verify SSL', 'type': 'bool'},
                {'name': consts.HTTPS_PROXY, 'title': 'HTTPS proxy', 'type': 'string'},
                {'name': 'create_group', 'title': 'Create asset group', 'type': 'bool'},
                {'name': 'group_name', 'title': 'Group name', 'type': 'string'},
                {'name': 'use_private_ips', 'title': 'Use private IP addresses', 'type': 'bool'},
                {'name': 'use_public_ips', 'title': 'Use public IP addresses', 'type': 'bool'},
                {'name': 'cidr_exclude_list', 'type': 'string', 'title': 'CIDRs exclude list'},
            ],
            'required': [consts.QUALYS_SCANS_DOMAIN,
                         consts.USERNAME,
                         consts.PASSWORD,
                         consts.VERIFY_SSL,
                         'create_group',
                         'use_private_ips',
                         'use_public_ips',
                         ],
            'type': 'array',
        }
        return schema

    @staticmethod
    def default_config() -> dict:
        return {
            consts.QUALYS_SCANS_DOMAIN: '',
            consts.USERNAME: '',
            consts.PASSWORD: '',
            consts.VERIFY_SSL: False,
            consts.HTTPS_PROXY: None,
            'group_name': '',
            'create_group': True,
            'use_private_ips': True,
            'use_public_ips': True,
            'cidr_exclude_list': '',
        }

    def _run(self) -> EntitiesResult:
        try:
            # pylint: disable=protected-access
            connection = QualysScansConnection(domain=self._config[consts.QUALYS_SCANS_DOMAIN],
                                               verify_ssl=self._config[consts.VERIFY_SSL],
                                               username=self._config.get(consts.USERNAME),
                                               password=self._config.get(consts.PASSWORD),
                                               https_proxy=self._config.get(consts.HTTPS_PROXY))
            current_result = self._get_entities_from_view({
                'adapters.data.network_interfaces.ips': 1,
                'internal_axon_id': 1
            })

            # ips_iter is a tuple of (ips, result).
            # result is equal success if we found ip.
            ips_iter = get_ips_from_view_as_iter(current_result,
                                                 self._config['use_public_ips'],
                                                 self._config['use_private_ips'],
                                                 True,
                                                 cidr_exclude_list=self._config.get('cidr_exclude_list'))

            results = []
            with connection:
                success_ips = []
                for ips, result in ips_iter:
                    if not result.successful or not ips:
                        results.append(result)
                        continue

                    exists_ips = connection.get_asset_by_ip(ips)
                    ips = list(set(ips) - set(exists_ips))
                    if not ips:
                        results.append(result)
                        continue

                    success, err_text = connection.add_assets_by_ip(ips)
                    if not success:
                        results.append(EntityResult(result.internal_axon_id, False, err_text))
                        continue

                    success_ips += ips
                    results.append(result)

                # If we fail to create group we are in a bad state.
                # On one hand, we've added assets and marked the ec as success,
                # but on the other hand we failed to create group and didn't report it to the user
                try:
                    if self._config['create_group'] and self._config.get('group_name'):
                        title = self._config.get('group_name')
                        id_ = connection.get_asset_group_id_by_title(title)
                        if id_:
                            success, err_text = connection.delete_group(id_)
                            if not success:
                                logger.error(f'Failed to delete group, error: {err_text}')
                        success, err_text = connection.create_group(title, success_ips)
                        if not success:
                            logger.error(f'Failed to create group, error: {err_text}')
                except Exception as e:
                    logger.exception('Failed to create group')
            return results
        except Exception:
            logger.exception(f'Problem with action Qualys IO create asset')
            return generic_fail(self._internal_axon_ids)
