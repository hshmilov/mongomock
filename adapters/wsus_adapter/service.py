import datetime
import ipaddress
import logging
import os
import re

from axonius.smart_json_class import SmartJsonClass

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES, DeviceAdapterOS
from axonius.fields import Field, ListField
from axonius.clients.rest.connection import RESTConnection
from axonius.utils.parsing import get_exception_string
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from wsus_adapter import consts
from wsus_adapter.connection import WsusWmiConnection

logger = logging.getLogger(f'axonius.{__name__}')


class UpdateSummary(SmartJsonClass):
    count_unknown = Field(int, 'Unknown')
    not_applicable = Field(int, 'Not Applicable')
    not_inst = Field(int, 'Not Installed')
    downloaded = Field(int, 'Downloaded')
    inst = Field(int, 'Installed')
    inst_pending = Field(int, 'Installed (Pending Reboot)')
    failed = Field(int, 'Failed')
    all_summed = Field(bool, 'All Updates Included in Summary')
    last_updated = Field(datetime.datetime, 'Last Updated')


class UpdateInfo(SmartJsonClass):
    install_state = Field(str, 'Installation State')
    approval_state = Field(str, 'Approval State')
    update_id = Field(str, 'Update ID')


class WsusAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        wsus_server = Field(str, 'WSUS Server GUID')
        last_sync_result = Field(str, 'Last Sync Result')
        last_sync_time = Field(datetime.datetime, 'Last Sync Time')
        last_reported_inventory_time = Field(datetime.datetime, 'Last Reported Inventory Time')
        last_reported_status_time = Field(datetime.datetime, 'Last Reported Status Time')
        role = Field(str, 'Computer Role')
        groups = ListField(str, 'Groups')
        summary = Field(UpdateSummary, 'Update Status Summary')
        update_info = ListField(UpdateInfo, 'Update Details')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))
        self._date_regex = re.compile('(-*\\d+)')

    def _get_client_id(self, client_config):
        return f'{client_config[consts.WSUS_HOST]}_{client_config[consts.USER]}'

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get(consts.WSUS_HOST))

    def _connect_client(self, client_config):
        try:
            connection = WsusWmiConnection(
                client_config[consts.WSUS_HOST],
                client_config[consts.USER],
                client_config[consts.PASSWORD],
                self._use_wmi_smb_path,
                self._python_27_path,
                # output_file=client_config.get(consts.WMI_OUTPUT_FILE),
                # working_dir=client_config.get(consts.WMI_WORKING_DIR)
            )
        except Exception as e:
            message = f'Error connecting to WSUS host: {str(client_config[consts.WSUS_HOST])}'
            logger.exception(message)
            raise ClientConnectionException(get_exception_string())
        else:
            return connection

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all computer targets from a specific WSUS server
        :param str client_name: The name of the client
        :param obj client_data: The data that represent a WSUS wmi connection

        :return: A json with all the attributes returned from the WSUS Server
        """
        yield from client_data.get_devices()

    def _clients_schema(self):
        return {
            'items': [
                {
                    'name': consts.WSUS_HOST,
                    'title': 'WSUS Server',
                    'type': 'string'
                },
                {
                    'name': consts.USER,
                    'title': 'User Name',
                    'type': 'string'
                },
                {
                    'name': consts.PASSWORD,
                    'title': 'Password',
                    'type': 'string',
                    'format': 'password'
                },
                # {
                #     'name': consts.WMI_WORKING_DIR,
                #     'title': 'Working Directory',
                #     'type': 'string',
                #     'default': consts.WMI_WORKING_DIR_DEFAULT
                # },
                # {
                #     'name': consts.WMI_OUTPUT_FILE,
                #     'title': 'Temporary Output File Name',
                #     'type': 'string'
                # }
            ],
            'required': [consts.WSUS_HOST, consts.USER, consts.PASSWORD],
            'type': 'array',
        }

    @property
    def _use_wmi_smb_path(self):
        return os.path.abspath(os.path.join(os.path.dirname(__file__), self.config['paths']['wmi_smb_path']))

    @property
    def _python_27_path(self):
        return self.config['paths']['python_27_path']

    def _parse_date(self, date_str):
        try:
            date_match = self._date_regex.findall(date_str)[0]
            date_int = int(date_match)
            if date_int > 0:
                return parse_date(date_int)
            return None
        except Exception as e:
            logger.warning(f'Failed to parse date {date_str}: {str(e)}')
            return None

    @staticmethod
    def _parse_approval_action(val):
        approval_action_values = {
            3: 'Not Approved',
            0: 'Approved',
            1: 'Remove',
            5: 'Bundled',
            2: 'Scan',
            -1: 'Unknown'
        }
        try:
            val = int(val)
        except ValueError:
            logger.warning(f'Failed to convert {val} to integer!')
        return approval_action_values.get(val, 'Unknown')

    @staticmethod
    def _parse_install_status(val):
        install_state_values = {
            3: 'Downloaded',
            4: 'Installed',
            6: 'Installed (pending reboot)',
            5: 'Failed',
            1: 'Not applicable',
            2: 'Not Installed',
            0: 'Unknown'
        }
        try:
            val = int(val)
        except ValueError:
            logger.warning(f'Failed to convert {val} to integer!')
        return install_state_values.get(val, 'Unknown')

    def _parse_update_summary(self, summary):
        if summary:
            try:
                update_date = self._parse_date(summary.get('LastUpdated'))
                summary = UpdateSummary(
                    count_unknown=summary.get('UnknownCount', -1),
                    not_applicable=summary.get('NotApplicableCount', -1),
                    not_inst=summary.get('NotInstalledCount', -1),
                    downloaded=summary.get('DownloadedCount', -1),
                    inst=summary.get('InstalledCount', -1),
                    inst_pending=summary.get('InstalledPendingRebootCount', -1),
                    failed=summary.get('FailedCount', -1),
                    all_summed=summary.get('IsSummedAcrossAllUpdates', False),
                    last_updated=update_date
                )
            except Exception as e:
                logger.warning(f'Failed to parse update summary from {summary}: {str(e)}')
                summary = None
        return summary

    def _parse_update_info(self, update_info_raw):
        update_info_list = list()
        for update_info in update_info_raw:
            try:
                state = update_info.get('UpdateInstallationState', -1)
                approval = update_info.get('UpdateApprovalAction', -1)
                update_id = update_info.get('UpdateId', None)
                if not update_id:
                    logger.warning(f'Got invalid update info {update_info}. Skipping.')
                    continue
                entry = UpdateInfo(
                    install_state=self._parse_install_status(state),
                    approval_state=self._parse_approval_action(approval),
                    update_id=update_id
                )
                update_info_list.append(entry)
            except Exception as e:
                logger.warning(f'Failed to parse update details from {update_info}: {str(e)}')
                continue
        return update_info_list

    # pylint: disable=too-many-branches, too-many-statements, too-many-locals, too-many-nested-blocks
    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device.wsus_server = device_raw.get('ParentServerId')
                device_id = device_raw.get('Id')
                if device_id is None:
                    logger.warning(f'Bad device with no ID {device_raw}')
                    continue
                device.id = str(device_id) + '_' + (device_raw.get('FullDomainName') or '')
                device.name = device_raw.get('FullDomainName')
                try:
                    if device_raw.get('IPAddress'):
                        # logger.info(f'XXXX IPAddress: {device_raw.get("IPAddress")}')
                        if device_raw.get('IPAddress').get('Address'):
                            ip_obj = ipaddress.ip_address(device_raw.get('IPAddress').get('Address'))
                            # logger.info(f'XXXX Got IP: {device_raw.get("IPAddress").get("Address")}')
                            device.add_nic(ips=[str(ip_obj)])
                except Exception as e:
                    logger.warning(f'Failed to parse IP info: {str(e)}')
                try:
                    domain_parts = device_raw.get('FullDomainName', '').split('.')
                    device.hostname = domain_parts[0]
                    device.domain = '.'.join(domain_parts[1:])
                except Exception:
                    message = f'Failed to parse device domain from {device_raw.get("FullDomainName")}!'
                    logger.exception(message)
                device.device_model = device_raw.get('Model')
                device.device_manufacturer = (device_raw.get('Make'))

                device.role = device_raw.get('ComputerRole')
                last_reported_status_time = self._parse_date(device_raw.get('LastReportedStatusTime'))
                device.last_reported_status_time = last_reported_status_time
                device.last_sync_result = device_raw.get('LastSyncResult')
                last_sync_time = self._parse_date(device_raw.get('LastSyncTime'))
                device.last_sync_time = last_sync_time
                last_reported_inventory_time = self._parse_date(device_raw.get('LastReportedInventoryTime'))
                device.last_reported_inventory_time = last_reported_inventory_time
                if last_reported_inventory_time and last_sync_time and last_reported_status_time:
                    device.last_seen = max(last_sync_time, last_reported_inventory_time, last_reported_status_time)
                else:
                    device.last_seen = last_sync_time or last_reported_inventory_time or last_reported_status_time
                device.add_agent_version(agent=AGENT_NAMES.wsus,
                                         version=device_raw.get('ClientVersion'))
                try:
                    bitness = device_raw.get('OSArchitecture')
                    device.os = DeviceAdapterOS()
                    if bitness:
                        device.os.bitness = 32 if '32' in bitness else 64
                    device.os.type = 'Windows'
                    device.os.build = device_raw.get('OSBuildNumber')
                    device.os.major = device_raw.get('OSMajorVersion')
                    device.os.minor = device_raw.get('OSMinorVersion')
                    device.os.sp = device_raw.get('OSServicePackMajorNumber')
                except Exception:
                    logger.exception(f'Prolbem with os for {device_raw}')
                device.bios_version = device_raw.get('BiosInfo', {}).get('Version')

                try:
                    group_ids = device_raw.get('RequestedTargetGroupNames')
                    if not isinstance(group_ids, list):
                        group_ids = []
                    for group_id in group_ids:
                        try:
                            device.groups.append(group_id)
                        except Exception:
                            logger.exception(f'Problem with group ID {group_id}')
                except Exception:
                    logger.exception(f'Problem getting groups')

                # summary
                summary_raw = device_raw.get('x_summary')
                summary = self._parse_update_summary(summary_raw)
                device.summary = summary
                # XXXX Removed update list section for performance reasons, until we find a better way to do this
                # update list
                # POP the update details to make the RAW smaller, this is a HUUUUGE list!
                # update_info_raw = device_raw.pop('x_updates_details', [])
                # update_info = self._parse_update_info(update_info_raw)
                # device.update_info = update_info
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem with device: {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
