import logging
from typing import List, Any

# pylint: disable=import-error
import oci
import oci.core
import oci.identity

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.oracle_cloud.connection import OracleCloudConnection
from axonius.clients.oracle_cloud.consts import SecurityRuleOrigin, OCI_PROTOCOLS_MAP, ORACLE_CLOUD_DOMAIN, \
    RULE_DIRECTION_INGRESS, RULE_DIRECTION_EGRESS
from axonius.clients.rest.connection import RESTConnection
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import parse_bool_from_raw, int_or_none, is_valid_ip
from axonius.clients.oracle_cloud import consts
from oracle_cloud_adapter.client_id import get_client_id
from oracle_cloud_adapter.oracle_cloud_cis import append_oracle_cloud_cis_data_to_device, \
    append_oracle_cloud_cis_data_to_user
from oracle_cloud_adapter.structures import OracleCloudVnic, OracleCloudDeviceInstance, OracleCloudNSGRule, \
    OracleCloudPortRange, OracleCloudUserInstance, OracleCloudUserCapabilities, OracleCloudUserApiKey

logger = logging.getLogger(f'axonius.{__name__}')


class OracleCloudAdapter(AdapterBase):
    class MyDeviceAdapter(OracleCloudDeviceInstance):
        pass

    class MyUserAdapter(OracleCloudUserInstance):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(ORACLE_CLOUD_DOMAIN)

    @staticmethod
    def get_connection(client_config):
        connection = OracleCloudConnection(client_config,
                                           client_config.pop('key_content', b''))
        with connection:
            pass
        return connection

    def _connect_client(self, client_config):
        try:
            file_content = self._grab_file_contents(client_config[consts.ORACLE_KEY_FILE])
            client_config_copy = client_config.copy()
            client_config_copy['key_content'] = file_content
            return self.get_connection(client_config_copy)
        except Exception as e:
            logger.error(f'Failed to connect client: {self._get_client_id(client_config)}')
            raise ClientConnectionException(str(e))

    # pylint: disable=arguments-differ
    @staticmethod
    def _query_users_by_client(client_name, client_data: OracleCloudConnection):
        with client_data:
            yield from client_data.get_users_list()

    # pylint: disable=arguments-differ
    @staticmethod
    def _query_devices_by_client(client_name, client_data: OracleCloudConnection):
        with client_data:
            yield from client_data.get_devices()

    @staticmethod
    def _clients_schema():
        """
        The schema OracleCloudAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': consts.ORACLE_CLOUD_USER,
                    'title': 'User OCID',
                    'type': 'string'
                },
                {
                    'name': consts.ORACLE_KEY_FILE,
                    'title': 'Oracle Key File',
                    'type': 'file'
                },
                {
                    'name': consts.ORACLE_FINGERPRINT,
                    'title': 'Key-Pair Fingerprint',
                    'type': 'string'
                },
                {
                    'name': consts.ORACLE_TENANCY,
                    'title': 'Tenancy OCID',
                    'type': 'string'
                },
                {
                    'name': consts.ORACLE_REGION,
                    'title': 'Oracle Cloud Infrastructure Region',
                    'type': 'string'
                },
            ],
            'required': [
                consts.ORACLE_CLOUD_USER,
                consts.ORACLE_KEY_FILE,
                consts.ORACLE_FINGERPRINT,
                consts.ORACLE_TENANCY,
                consts.ORACLE_REGION
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches
    @staticmethod
    def _parse_device_network_info(device: OracleCloudDeviceInstance,
                                   vnics_raw: List[oci.core.models.Vnic]):
        """
        Parse vnics for device, and extract NIC information.
        """
        if not isinstance(vnics_raw, list):
            logger.warning(f'Unexpected type in network info for {device.get_field_safe("id")}: '
                           f'{type(vnics_raw)}. Expected a list')
            return
        vnics = list()
        for vnic_raw in vnics_raw:
            vnic_raw: oci.core.models.Vnic  # type hint
            # add public ip
            device.add_public_ip(vnic_raw.public_ip)
            # try to extract more nic info
            try:
                private_ip = vnic_raw.private_ip if is_valid_ip(vnic_raw.private_ip) else None
                if vnic_raw.mac_address and private_ip:
                    device.add_nic(mac=vnic_raw.mac_address, ips=[private_ip], name=vnic_raw.display_name)
                elif vnic_raw.mac_address:
                    device.add_nic(mac=vnic_raw.mac_address, name=vnic_raw.display_name)
                elif private_ip:
                    device.add_ips_and_macs(ips=[private_ip])
            except Exception as e:
                logger.warning(f'Failed to parse NIC from VNIC: {vnic_raw}. Error: {str(e)}')
            # See if we need to set a hostname
            if vnic_raw.hostname_label and not device.get_field_safe('hostname'):
                device.hostname = vnic_raw.hostname_label
            # Still try to create vnic object
            try:
                vnic = OracleCloudVnic(
                    id=vnic_raw.id,
                    display_name=vnic_raw.display_name,
                    hostname_label=vnic_raw.hostname_label,
                    compartment_id=vnic_raw.compartment_id,
                    is_primary=parse_bool_from_raw(vnic_raw.is_primary),
                    lifecycle_state=vnic_raw.lifecycle_state,
                    subnet_id=vnic_raw.subnet_id,
                    vlan_id=vnic_raw.vlan_id,
                    time_created=parse_date(vnic_raw.time_created),
                )
                if vnic_raw.nsg_ids and isinstance(vnic_raw.nsg_ids, list):
                    vnic.nsg_ids = vnic_raw.nsg_ids
                try:
                    vnic.mac_address = vnic_raw.mac_address
                except Exception as e:
                    logger.warning(f'Failed to parse mac from {vnic_raw}: {str(e)}')
                try:
                    if vnic_raw.private_ip:
                        vnic.private_ip = vnic_raw.private_ip
                        vnic.private_ip_raw = [vnic_raw.private_ip]
                    if vnic_raw.public_ip:
                        vnic.public_ip = vnic_raw.public_ip
                        vnic.public_ip_raw = [vnic_raw.public_ip]
                except Exception as e:
                    logger.warning(f'Failed to parse IPs from {vnic_raw}: {str(e)}')
            except Exception as e:
                logger.warning(f'Failed to parse vnic {vnic_raw}: {str(e)}')
                continue
            else:
                vnics.append(vnic)
        device.vnics = vnics

    @classmethod
    def _get_rules_from_vcn_infos(cls, vcn_infos):
        if not isinstance(vcn_infos, list):
            logger.warning(f'Unexpected type of vcn info {type(vcn_infos)}. Expected a list.')
            return

        for vcn_raw_dict in vcn_infos:
            if not isinstance(vcn_raw_dict, dict):
                logger.warning(f'Unexpected type of vcn info dict. Expected dict, got type {type(vcn_raw_dict)}')
                continue
            sec_lists_raw = vcn_raw_dict.get('sec_lists')
            default_sec_list = vcn_raw_dict.get('default_sec_list')
            vcn_rules = list()
            if default_sec_list:
                vcn_rules.extend(cls._standardize_seclist_rules(default_sec_list, True))
            if sec_lists_raw and isinstance(sec_lists_raw, list):
                for sec_list in sec_lists_raw:
                    vcn_rules.extend(cls._standardize_seclist_rules(sec_list, False))
            yield from vcn_rules

    @staticmethod
    def _standardize_seclist_rules(seclist_raw: oci.core.models.SecurityList, is_default_seclist: bool):
        ingress_rules = seclist_raw.ingress_security_rules
        egress_rules = seclist_raw.egress_security_rules
        all_rules = list()
        if ingress_rules and isinstance(ingress_rules, list):
            for i, rule in enumerate(ingress_rules):
                rule.destination = None
                rule.destination_type = None
                rule.direction = RULE_DIRECTION_INGRESS
                rule.id = f'{RULE_DIRECTION_INGRESS}_{seclist_raw.id}_{i}'
                all_rules.append(rule)
        if egress_rules and isinstance(egress_rules, list):
            for i, rule in enumerate(egress_rules):
                rule.source = None
                rule.source_type = None
                rule.direction = RULE_DIRECTION_EGRESS
                rule.id = f'{RULE_DIRECTION_EGRESS}_{seclist_raw.id}_{i}'
                all_rules.append(rule)

        for rule in all_rules:
            rule.is_default = parse_bool_from_raw(is_default_seclist)
            rule.vcn_id = seclist_raw.vcn_id
            rule.compartment_id = seclist_raw.compartment_id
            rule.time_created = seclist_raw.time_created
            rule.seclist_id = seclist_raw.id
            rule.is_valid = None

        return all_rules

    # pylint: disable=too-many-branches, too-many-statements
    @staticmethod
    def _parse_nsg_rules(device: OracleCloudDeviceInstance,
                         nsgs_raw: list):
        """
        Parse nsg security rules for device, and extract firewall and open port information.
        """
        if not isinstance(nsgs_raw, list):
            logger.warning(f'Unexpected type in nsg info for {device.get_field_safe("id")}: '
                           f'{type(nsgs_raw)}. Expected a list')
            return
        known_ids = set()  # To avoid possible duplicates
        if not device.get_field_safe('nsg_rules'):
            device.nsg_rules = list()
        if not device.get_field_safe('vcn_ids'):
            device.vcn_ids = list()
        for nsg_raw in nsgs_raw:
            if nsg_raw.id in known_ids:
                logger.debug(f'Duplicate id: {nsg_raw.id}')
                continue
            known_ids.add(nsg_raw.id)
            # Extract open ports
            protocol_raw = OCI_PROTOCOLS_MAP.get(nsg_raw.protocol, nsg_raw.protocol)
            opts: Any = None
            to_port: Any = None  # min port
            from_port: Any = None  # max port
            if protocol_raw.startswith('TCP'):
                opts: oci.core.models.TcpOptions = nsg_raw.tcp_options  # I love type hints
            elif protocol_raw.startswith('UDP'):
                opts: oci.core.models.UdpOptions = nsg_raw.udp_options  # They make life so much better
            if opts:
                if not (opts.destination_port_range or opts.source_port_range):
                    pass
                    # No port range means ALL
                elif opts.destination_port_range:
                    to_port = opts.destination_port_range.max
                    from_port = opts.destination_port_range.min
            # Check if it's one specific port that's opened
            if from_port is not None and \
                    from_port == to_port and \
                    parse_bool_from_raw(nsg_raw.is_valid) is True:
                try:
                    device.add_open_port(
                        protocol_raw,
                        int_or_none(to_port)
                    )
                except Exception as e:
                    logger.warning(f'Failed to add open port: {str(e)}')
                    # keep going
            try:
                device.add_firewall_rule(
                    name=nsg_raw.description or nsg_raw.id,
                    source=nsg_raw.source,
                    type='Allow',
                    direction=nsg_raw.direction,
                    target=nsg_raw.destination,
                    protocol=protocol_raw,
                    to_port=int_or_none(to_port),
                    from_port=int_or_none(from_port),
                )
            except Exception as e:
                logger.warning(f'Failed to extract FirewallRule from nsg rule {nsg_raw}: {str(e)}')
                # keep going, try to do other things

            # Create NSG Rule object
            try:
                nsg = OracleCloudNSGRule(
                    description=nsg_raw.description,
                    dest=nsg_raw.destination,
                    dest_type=nsg_raw.destination_type,
                    direction=nsg_raw.direction,
                    rule_id=nsg_raw.id,
                    is_stateless=parse_bool_from_raw(nsg_raw.is_stateless),
                    is_valid=parse_bool_from_raw(nsg_raw.is_valid),
                    protocol=protocol_raw,
                    src=nsg_raw.source,
                    src_type=nsg_raw.source_type,
                    time_created=parse_date(nsg_raw.time_created),
                )
                if opts and opts.destination_port_range:
                    nsg.dst_port_range = OracleCloudPortRange(
                        min_port=int_or_none(opts.destination_port_range.min),
                        max_port=int_or_none(opts.destination_port_range.max))
                if opts and opts.source_port_range:
                    src_port_range = OracleCloudPortRange(
                        min=int_or_none(opts.source_port_range.min),
                        max=int_or_none(opts.source_port_range.max))
                    nsg.src_port_range = src_port_range
                # Add case for security list rules
                if hasattr(nsg_raw, 'seclist_id'):
                    nsg.origin = SecurityRuleOrigin.SECLIST.value
                    nsg.sec_list_id = nsg_raw.seclist_id
                else:
                    nsg.origin = SecurityRuleOrigin.NSG.value
                if hasattr(nsg_raw, 'is_default'):
                    nsg.is_default = parse_bool_from_raw(nsg_raw.is_default)
                if hasattr(nsg_raw, 'vcn_id'):
                    nsg.vcn_id = nsg_raw.vcn_id
                    if nsg_raw.vcn_id not in device.vcn_ids:
                        device.vcn_ids.append(nsg_raw.vcn_id)
                if hasattr(nsg_raw, 'compartment_id'):
                    nsg.compartment_id = nsg_raw.compartment_id
            except Exception as e:
                logger.exception(f'Failed to parse NSG info from {nsg_raw}: {str(e)}')
                continue
            else:
                device.nsg_rules.append(nsg)

    @classmethod
    def _fill_oracle_device_fields(cls, device: OracleCloudDeviceInstance, device_raw_all: dict):
        device_raw: oci.core.models.Instance = device_raw_all.get('general_info')
        if not (device_raw and isinstance(device_raw, oci.core.models.Instance)):
            logger.error(f'Unable to parse device general info: {device_raw}')
            return
        device.oci_compartment = device_raw.compartment_id
        device.oci_region = device_raw.region
        device.time_created = parse_date(device_raw.time_created)
        device.tenancy = device_raw_all.get('tenancy')
        device.dedicated_vm_host_id = device_raw.dedicated_vm_host_id
        device.fault_domain = device_raw.fault_domain
        device.launch_mode = device_raw.launch_mode
        device.lifecycle_state = device_raw.lifecycle_state
        device.instance_shape = device_raw.shape
        device.availability_domain = device_raw.availability_domain
        device.maint_reboot_due = parse_date(device_raw.time_maintenance_reboot_due)
        try:
            device.vcn_ids = device_raw_all.get('vcn_ids') or []
        except Exception as e:
            logger.warning(f'Failed to parse vcn ids: {str(e)}')

        device_vnics_raw = list(device_raw_all.get('network_info')) or []
        if device_vnics_raw:
            try:
                cls._parse_device_network_info(device, device_vnics_raw)
            except Exception:
                logger.exception(f'Failed to parse network info for device {device.get_field_safe("id")}')

        device_vcns_raw = list(device_raw_all.get('vcn_infos')) or []
        nsgs = []
        if device_vcns_raw:
            try:
                nsgs = cls._get_rules_from_vcn_infos(device_vcns_raw)
            except Exception:
                logger.exception(f'Failed to parse vcn info for device {device.get_field_safe("id")}')

        device_nsgs_raw = list(device_raw_all.get('network_security_rules')) or []
        all_nsgs = device_nsgs_raw + list(nsgs)
        if all_nsgs:
            try:
                cls._parse_nsg_rules(device, all_nsgs)
            except Exception:
                logger.exception(f'Failed to parse NSG Security Rules for device: {device.get_field_safe("id")}')

    def _handle_cis_for_device(self, device: OracleCloudDeviceInstance):
        device.oracle_cloud_account_id = device.get_field_safe('tenancy')
        device.oracle_cloud_cis_incompliant = []  # Remove old rules which may be irrelevant now
        if self.should_cloud_compliance_run():
            append_oracle_cloud_cis_data_to_device(device)

    def create_device(self, device_raw_all):
        try:
            device = self._new_device_adapter()
            device_raw = device_raw_all.get('general_info')
            device_tenancy = device_raw_all.get('tenancy')
            try:
                device_id = device_raw.id
                if not device_id:
                    logger.error(f'Bad device with no ID {device_raw}')
                    return None
                device.id = '_'.join([device_id, device_tenancy or ''])
            except Exception:
                logger.exception(f'Bad device with no ID {device_raw_all}')
                return None
            try:
                device.name = device_raw.display_name
                device.first_seen = parse_date(device_raw.time_created)
                device.cloud_id = device_id
                device.cloud_provider = 'Oracle Cloud'
                device.uuid = device_id
            except Exception:
                logger.exception(f'Failed to create general-info device {device_raw}.')
            # Now to handle specific info, as well as network interfaces and firewall rules
            try:
                self._fill_oracle_device_fields(device, device_raw_all)
            except Exception:
                logger.exception(f'Failed to parse network information for device {device_raw}')
            try:
                self._handle_cis_for_device(device)
            except Exception:
                logger.exception(f'Failed to parse CIS data for device {device_raw}')
            device.set_raw(OracleCloudConnection.serialize_device_dict(device_raw_all))
            return device
        except Exception:
            logger.exception(f'Failed to create device {device_raw_all}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self.create_device(device_raw)
            if device:
                yield device

    @staticmethod
    def _fill_oracle_user_fields(user: OracleCloudUserInstance,
                                 user_raw: oci.identity.models.User):
        user.oci_ocid = user_raw.id
        user.oci_compartment = user_raw.compartment_id
        user.is_email_verified = parse_bool_from_raw(user_raw.email_verified)
        user.is_mfa_active = parse_bool_from_raw(user_raw.is_mfa_activated)
        user.external_identifier = user_raw.external_identifier
        user.identity_provider_id = user_raw.identity_provider_id
        user.lifecycle_state = user_raw.lifecycle_state
        try:
            user.capabilities = OracleCloudUserCapabilities(
                can_use_console_passwd=parse_bool_from_raw(user_raw.capabilities.can_use_console_password),
                can_use_api_keys=parse_bool_from_raw(user_raw.capabilities.can_use_api_keys),
                can_use_auth_tokens=parse_bool_from_raw(user_raw.capabilities.can_use_auth_tokens),
                can_use_smtp_creds=parse_bool_from_raw(user_raw.capabilities.can_use_smtp_credentials),
                can_use_customer_secret_keys=parse_bool_from_raw(user_raw.capabilities.can_use_customer_secret_keys),
                can_use_oauth2_client_creds=parse_bool_from_raw(
                    user_raw.capabilities.can_use_o_auth2_client_credentials),
            )
        except Exception as e:
            logger.warning(f'Failed to parse user capabilities: {str(e)}')
        if hasattr(user_raw, 'x_api_keys') and user_raw.x_api_keys:
            api_keys = list()
            for key in user_raw.x_api_keys:
                try:
                    api_key = OracleCloudUserApiKey(
                        key_id=key.key_id,
                        time_created=parse_date(key.time_created),
                        fingerprint=key.fingerprint
                    )
                    api_keys.append(api_key)
                except Exception as e:
                    logger.debug(f'Failed to parse key info {key} : {str(e)}')
            user.api_keys = api_keys

    def _handle_cis_for_user(self, user: OracleCloudUserInstance):
        user.oracle_cloud_account_id = user.get_field_safe('oci_compartment')
        user.oracle_cloud_cis_incompliant = []  # remove old rules
        if self.should_cloud_compliance_run():
            append_oracle_cloud_cis_data_to_user(user)

    def create_user(self, user_raw: oci.identity.models.User):
        try:
            user = self._new_user_adapter()
            user_id = user_raw.id
            if not user_id:
                logger.error(f'Bad user with no id: {user_raw}')
                return None
            user.id = f'{user_id}_{user_raw.compartment_id}'
            user.username = user_raw.name
            user.display_name = user_raw.name
            user.description = user_raw.description or None
            user.mail = user_raw.email
            user.user_created = parse_date(user_raw.time_created)
            user.user_status = user_raw.lifecycle_state
            if hasattr(user_raw, 'x_groups') and isinstance(user_raw.x_groups, list):
                groups = list()
                for group in user_raw.x_groups:
                    try:
                        groups.append(group.name)
                        user.is_admin = user.get_field_safe('is_admin') or 'admin' in group.name.lower()
                    except Exception as e:
                        logger.warning(f'Failed to parse user groups and admin status from {group}: {str(e)}')
                user.groups = groups
            try:
                self._fill_oracle_user_fields(user, user_raw)
            except Exception as e:
                logger.warning(f'Failed to parse specific info for {user_id}: {str(e)}')
                logger.debug(f'Failed to parse specific info for {user_raw}', exc_info=True)  # detailed debug msg
            try:
                self._handle_cis_for_user(user)
            except Exception:
                logger.exception(f'Failed to parse cis data for user: {user_raw}')
            user.set_raw(OracleCloudConnection.serialize_user(user_raw))
            return user
        except Exception:
            logger.exception(f'Failed to create user {user_raw}')
            return None

    def _parse_users_raw_data(self, users_raw_data):
        for user_raw in users_raw_data:
            user = self.create_user(user_raw)
            if user:
                yield user

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.Cloud_Provider, AdapterProperty.UserManagement]
