# pylint: disable=too-many-branches, too-many-nested-blocks
import logging

from axonius.clients.azure.client import AzureCloudConnection
from compliance.utils.AzureAccountReport import AzureAccountReport
from compliance.utils.account_report import RuleStatus
from compliance.utils.cis_utils import cis_rule, errors_to_gui, bad_api_response, good_api_response, get_api_error, \
    get_api_data

logger = logging.getLogger(f'axonius.{__name__}')


def get_all_vms(azure: AzureCloudConnection):
    responses = {}
    for subscription_id, subscription_data in azure.all_subscriptions.items():
        subscription_name = subscription_data.get('displayName') or subscription_id

        try:
            response = dict()
            for vm in azure.compute.get_all_vms(subscription_id):
                response[vm['id'].lower()] = vm
        except Exception as e:
            logger.exception('Exception while getting virtual machines')
            return bad_api_response(f'Error getting virtual machines '
                                    f'(/subscription/{subscription_id}/providers/Microsoft.Compute/'
                                    f'virtualMachines?api-version=2020-06-01): '
                                    f'{str(e)}')

        responses[subscription_name] = response

    return good_api_response(responses)


def get_all_disks(azure: AzureCloudConnection):
    responses = {}
    for subscription_id, subscription_data in azure.all_subscriptions.items():
        subscription_name = subscription_data.get('displayName') or subscription_id
        response = dict()
        try:
            for disk in azure.compute.get_all_disks(subscription_id):
                response[disk['id'].lower()] = disk
        except Exception as e:
            logger.exception('Exception while getting virtual machines')
            return bad_api_response(f'Error getting disks '
                                    f'(/subscription/{subscription_id}/providers/Microsoft.Compute/'
                                    f'disks?api-version=2020-05-01): '
                                    f'{str(e)}')

        responses[subscription_name] = response

    return good_api_response(responses)


class CISAzureCategory7:
    def __init__(self, report: AzureAccountReport, azure: AzureCloudConnection, account_dict: dict):
        self.report = report
        self.azure = azure
        self._account_dict = account_dict.copy()
        self._vms = get_all_vms(azure)
        self._vms_disks = get_all_disks(azure)

    @staticmethod
    def is_disk_encrypted(disk: dict) -> bool:
        return str(((disk.get('properties') or {}).get('encryption') or {}).get('type')).lower() in [
            'encryptionatrestwithplatformkey', 'encryptionatrestwithcustomerkey'
        ]

    @cis_rule('7.1')
    def check_cis_azure_7_1(self, **kwargs):
        """
        7.1 Ensure that 'OS disk' are encrypted
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self._vms)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        error = get_api_error(self._vms_disks)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        all_vms = get_api_data(self._vms)
        all_vms_disks = get_api_data(self._vms_disks)
        total_resources = 0
        errors = []

        for subscription_name, all_vms_per_subscription in all_vms.items():
            for vm in all_vms_per_subscription.values():
                total_resources += 1
                vm_name = vm.get('name') or vm['id']
                try:
                    os_disk = ((vm.get('properties') or {}).get('storageProfile') or {}).get('osDisk') or {}
                    os_disk_id = (os_disk.get('managedDisk') or {}).get('id')

                    if not os_disk_id:
                        logger.error(f'Did not found os disk id. OS disk: {str(os_disk)}')
                        raise ValueError(f'OS Disk ID not found in VM details')

                    disk = (all_vms_disks.get(subscription_name) or {}).get(os_disk_id.lower())
                    if not disk:
                        raise ValueError(f'OS Disk not found in disks')

                    try:
                        result = self.is_disk_encrypted(disk)
                    except Exception as e2:
                        raise ValueError(f'Could not determine encryption status: {str(e2)}')

                    if not result:
                        raise ValueError(f'OS Disk is not encrypted')

                except Exception as e:
                    errors.append(
                        f'Subscription "{subscription_name}" - VM {vm_name!r}: {str(e)}'
                    )
                    continue

        if errors:
            self.report.add_rule(
                RuleStatus.Failed,
                rule_section,
                (len(errors), total_resources),
                0,
                errors_to_gui(errors)
            )
        else:
            self.report.add_rule(
                RuleStatus.Passed,
                rule_section,
                (0, total_resources),
                0,
                ''
            )

    @cis_rule('7.2')
    def check_cis_azure_7_2(self, **kwargs):
        """
        7.2 Ensure that 'Data disks' are encrypted
        """
        # pylint: disable=too-many-locals
        rule_section = kwargs['rule_section']
        error = get_api_error(self._vms)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        error = get_api_error(self._vms_disks)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        all_vms = get_api_data(self._vms)
        all_vms_disks = get_api_data(self._vms_disks)
        total_resources = 0
        errors = []

        for subscription_name, all_vms_per_subscription in all_vms.items():
            for vm in all_vms_per_subscription.values():
                total_resources += 1
                vm_name = vm.get('name') or vm['id']
                try:
                    data_disks = ((vm.get('properties') or {}).get('storageProfile') or {}).get('dataDisks') or []
                    for data_disk in data_disks:
                        data_disk_id = (data_disk.get('managedDisk') or {}).get('id')

                        if not data_disk_id:
                            logger.error(f'Did not found data disk id. OS disk: {str(data_disk)}')
                            raise ValueError(f'Data Disk ID not found in VM details')

                        disk = (all_vms_disks.get(subscription_name) or {}).get(data_disk_id.lower())
                        if not disk:
                            raise ValueError(f'Data Disk not found in disks')

                        try:
                            result = self.is_disk_encrypted(disk)
                        except Exception as e2:
                            raise ValueError(f'Could not determine encryption status: {str(e2)}')

                        if not result:
                            raise ValueError(f'Data Disk is not encrypted')

                except Exception as e:
                    errors.append(
                        f'Subscription "{subscription_name}" - VM {vm_name!r}: {str(e)}'
                    )
                    continue

        if errors:
            self.report.add_rule(
                RuleStatus.Failed,
                rule_section,
                (len(errors), total_resources),
                0,
                errors_to_gui(errors)
            )
        else:
            self.report.add_rule(
                RuleStatus.Passed,
                rule_section,
                (0, total_resources),
                0,
                ''
            )

    @cis_rule('7.3')
    def check_cis_azure_7_3(self, **kwargs):
        """
        7.3 Ensure that 'Unattached disks' are encrypted
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self._vms_disks)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        all_vms_disks = get_api_data(self._vms_disks)
        total_resources = 0
        errors = []

        for subscription_name, all_disks_in_subscription in all_vms_disks.items():
            for disk in all_disks_in_subscription.values():
                disk_properties = disk.get('properties') or {}
                disk_name = disk.get('name') or disk.get('id')
                if str(disk_properties.get('diskState')).lower() == 'attached':
                    continue

                total_resources += 1

                if not self.is_disk_encrypted(disk):
                    errors.append(
                        f'Subscription "{subscription_name}": Disk {disk_name!r} is not encrypted'
                    )

        if errors:
            self.report.add_rule(
                RuleStatus.Failed,
                rule_section,
                (len(errors), total_resources),
                0,
                errors_to_gui(errors)
            )
        else:
            self.report.add_rule(
                RuleStatus.Passed,
                rule_section,
                (0, total_resources),
                0,
                ''
            )
