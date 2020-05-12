import logging
from collections import defaultdict

import chardet

from axonius.adapter_base import AdapterProperty
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field, ListField
from axonius.scanner_adapter_base import ScannerAdapterBase
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import make_dict_from_csv

logger = logging.getLogger(f'axonius.{__name__}')


class VulnStatus(SmartJsonClass):
    track_id = Field(str, 'Tracking ID')
    edfs_owner = Field(str, 'Owner')
    src = Field(str, 'Source')
    edfs_domain = Field(str, 'Domain Name')
    edfs_ip = Field(str, 'IP Address')
    is_corporate = Field(bool, 'Corporate')
    is_customer = Field(bool, 'Is Customer')
    pmi = Field(bool, 'PMI')
    edfs_cloud = Field(bool, 'Cloud (EDFS)')
    owner_status = Field(str, 'Owner Status')
    owner_confirm = Field(str, 'Owner Confirmation')
    vulnerability = Field(str, 'Vulnerability')
    count_cve = Field(int, 'CVE Count')
    finding = Field(str, 'Finding')
    descr = Field(str, 'Finding Description')
    solution = Field(str, 'Vulnerability Solution')
    soc_status = Field(str, 'SOC Status')
    owner_response = Field(str, 'Owner Response')
    vuln_status = Field(str, 'Vulnerability Status')


class EdfsCsvAdapter(ScannerAdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        vuln_status = ListField(VulnStatus, 'Vulnerability Status')
        edfs_domain = Field(str, 'Domain Name')
        is_vuln = Field(bool, 'Vulnerable Asset')
        known_ip = Field(bool, 'Known IP Address')
        is_live = Field(bool, 'Live Known Asset')
        is_corporate = Field(bool, 'Is Corporate')
        is_customer = Field(bool, 'Is Customer')
        pmi = Field(bool, 'PMI')
        edfs_cloud = Field(bool, 'Cloud (EDFS)')
        amdocsip = Field(bool, 'AmdocsIP')
        rapidseven = Field(bool, 'Rapid7')
        panorays = Field(bool, 'Panorays')
        shodan = Field(bool, 'Shodan')
        riskiq = Field(bool, 'RiskIQ')
        riskiq_v2 = Field(bool, 'RiskIQ V2')
        nw_team = Field(bool, 'NW Team')
        brand = Field(str, 'Brand')
        asn = Field(str, 'ASN')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return f'EDFS_{client_config["edfs_external_status_label"]}_{client_config["edfs_vuln_status_label"]}'

    @staticmethod
    def _test_reachability(client_config):
        raise NotImplementedError()

    def _create_csv_data_from_file(self, csv_file):
        csv_data_bytes = self._grab_file_contents(csv_file)

        encoding = chardet.detect(csv_data_bytes)['encoding']  # detect decoding automatically
        encoding = encoding or 'utf-8'
        csv_data = csv_data_bytes.decode(encoding)
        csv_dict = make_dict_from_csv(csv_data)
        return csv_dict

    def _connect_client(self, client_config):
        self._create_csv_data_from_file(client_config['edfs_external_status_csv'])
        self._create_csv_data_from_file(client_config['edfs_vuln_status_csv'])
        return client_config

    def _query_devices_by_client(self, client_name, client_data):
        external_data = self._create_csv_data_from_file(client_data['edfs_external_status_csv'])
        vuln_data = self._create_csv_data_from_file(client_data['edfs_vuln_status_csv'])
        return external_data, vuln_data

    @staticmethod
    def _clients_schema():
        """
        The schema EdfsCsvAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'edfs_external_status_label',
                    'title': 'External Amdocs assets CSV file name',
                    'type': 'string',
                },
                {
                    'name': 'edfs_external_status_csv',
                    'title': 'External Amdocs assets CSV file',
                    'type': 'file',
                    'description': 'The binary contents of the csv',
                },
                {
                    'name': 'edfs_vuln_status_label',
                    'title': 'External Amdocs assets vulns CSV file name',
                    'type': 'string'
                },
                {
                    'name': 'edfs_vuln_status_csv',
                    'title': 'External Amdocs assets vulns CSV file',
                    'type': 'file',
                    'description': 'The binary contents of the csv',
                }

            ],
            'required': [
                'edfs_external_status_label',
                'edfs_external_status_csv',
                'edfs_vuln_status_label',
                'edfs_vuln_status_csv'
            ],
            'type': 'array'
        }

    def _parse_raw_data(self, devices_raw_data):
        def _make_bool_from_data(data_field):
            if not isinstance(data_field, str):
                return False
            if data_field.lower().strip() == 'yes':
                return True
            return False
        external_assets, vuln_statuses = devices_raw_data
        vuln_status_dict = defaultdict(list)
        # populate vulnaerability status dict with lists of VulnStatus objects
        # based on the IP Address of the item
        for vuln_raw in vuln_statuses:
            key = vuln_raw.get('IP Address')
            if not key:
                continue
            try:
                count_cve = int(vuln_raw.get('# CVE'))
            except Exception:
                count_cve = None
            try:
                vuln_status_dict[key].append(VulnStatus(
                    track_id=vuln_raw.get('Tracking ID'),
                    edfs_owner=vuln_raw.get('Owner'),
                    src=vuln_raw.get('Source'),
                    edfs_domain=vuln_raw.get('Domain Name'),
                    edfs_ip=vuln_raw.get('IP Address'),
                    is_corporate=_make_bool_from_data(vuln_raw.get('Corporate')),
                    is_customer=_make_bool_from_data(vuln_raw.get('Customer')),
                    pmi=_make_bool_from_data(vuln_raw.get('PMI')),
                    edfs_cloud=_make_bool_from_data(vuln_raw.get('Cloud')),
                    owner_status=vuln_raw.get('Owner Status'),
                    owner_confirm=vuln_raw.get('Owner confirmation'),
                    vulnerability=vuln_raw.get('Vulnerability'),
                    count_cve=count_cve,
                    finding=vuln_raw.get('Finding'),
                    descr=vuln_raw.get('Description'),
                    solution=vuln_raw.get('Vulnerability Solution'),
                    owner_response=vuln_raw.get('Owner Response'),
                    vuln_status=vuln_raw.get('Vulnerability Status')
                ))
            except Exception as e:
                logger.warning(f'Got {str(e)} when parsing row: {vuln_raw}')

        # now create devices and match vuln data for them

        for device_raw in external_assets:
            try:
                device = self._new_device_adapter()
                device_id = device_raw.get('Public IP Address')
                if not device_id:
                    logger.warning(f'Bad device with no ID: {device_raw}')
                    continue
                device.id = f'{device_id}_{device_raw.get("Owner") or ""}'
                # The next line may raise an exception. This is intended.
                device.add_public_ip(device_id)
                # The next line may also raise an exception. This is also intended.
                device.add_ips_and_macs(ips=[device_id])
                # Now for the adapter-specific stuff
                device.owner = device_raw.get('Owner')
                device.edfs_domain = device_raw.get('Domain Name')
                device.is_vuln = _make_bool_from_data(device_raw.get('Vulnerable Asset'))
                device.known_ip = _make_bool_from_data(device_raw.get('Known IP Address'))
                device.is_live = _make_bool_from_data(device_raw.get('Live Known Asset'))
                device.is_corporate = _make_bool_from_data(device_raw.get('Corporate'))
                device.is_customer = _make_bool_from_data(device_raw.get('Customer'))
                device.pmi = _make_bool_from_data(device_raw.get('PMI'))
                device.edfs_cloud = _make_bool_from_data(device_raw.get('Cloud'))
                device.amdocsip = _make_bool_from_data(device_raw.get('Amdocsip'))
                device.rapidseven = _make_bool_from_data(device_raw.get('Rapid7'))
                device.panorays = _make_bool_from_data(device_raw.get('Panorays'))
                device.shodan = _make_bool_from_data(device_raw.get('Shodan'))
                device.riskiq = _make_bool_from_data(device_raw.get('RiskIQ'))
                device.riskiq_v2 = _make_bool_from_data(device_raw.get('RiskIQ V2'))
                device.nw_team = _make_bool_from_data(device_raw.get('NW Team'))
                device.brand = device_raw.get('Brand')
                device.asn = device_raw.get('ASN')
                # Now add the vulnerability statuses
                device.vuln_status = vuln_status_dict[device_id]
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem adding device: {str(device_raw)}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
