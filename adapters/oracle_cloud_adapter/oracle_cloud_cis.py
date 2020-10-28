"""
Oracle Cloud Cis helpers
"""
# pylint: disable=too-many-branches, too-many-nested-blocks
import datetime
import logging
from typing import List

from axonius.clients.oracle_cloud.consts import SecurityRuleOrigin, OCI_PROTOCOLS_MAP, CIS_API_KEY_ROTATION_DAYS, \
    RULE_DIRECTION_INGRESS
from axonius.utils.datetime import parse_date
from axonius.utils.parsing import int_or_none
from oracle_cloud_adapter.structures import OracleCloudDeviceInstance, OracleCloudUserInstance, OracleCloudNSGRule, \
    OracleCloudUserApiKey

logger = logging.getLogger(f'axonius.{__name__}')

PORT_RDP = 3389
PORT_SSH = 22
PROTOCOLS = ['tcp', 'all', '6']
PERMISSIVE_DESTINATION_RULES = ['*', '0.0.0.0', 'internet', 'any', 'all']
CIDR_BLOCK_ALL = '/0'


def is_nsg_allow_inbound_internet(nsg_rule: OracleCloudNSGRule,
                                  port: int,
                                  origin=SecurityRuleOrigin.SECLIST,
                                  only_default_rules=False) -> bool:
    """
    Check a nsg rule to see if a port is accessible from the internet
    :param nsg_rule: network security group rule to check
    :param port: port to check
    :param origin: Origin of security rule (one of `SecurityRuleOrigin` enum)
    :param only_default_rules: Only looking for rules that are the default on a VCN.
    :return: True if port is not restricted from the internet
    """
    properties = nsg_rule.to_dict()
    if not properties:
        logger.debug(f'Empty nsg rule: {nsg_rule}')
        return False
    # Rules can have origin == 'NSG' or 'Security List'. Usually we're only looking for 'Security List'.
    if properties.get('origin') != origin.value:
        return False
    # If only_default_rules is set, we're only looking at rules that are default for a VCN
    if only_default_rules and not properties.get('is_default'):
        return False
    # Only applies to ingress rules
    if str(properties.get('direction')).upper() != RULE_DIRECTION_INGRESS:
        return False

    rule_protocol = str(properties.get('protocol'))
    rule_protocol = str(OCI_PROTOCOLS_MAP.get(rule_protocol, rule_protocol)).lower()

    # complex sub-fields are not processed by SmartJsonClass.to_dict() so we need to get them ourselves
    dst_port_range = nsg_rule.get_field_safe('dst_port_range') or {}
    if not isinstance(dst_port_range, dict):
        try:
            dst_port_range = dst_port_range.to_dict()
        except Exception:
            logger.exception(f'Error handling port range {dst_port_range}')
            dst_port_range = {}
    port_min = 0
    port_max = 0
    if dst_port_range:
        port_min = int_or_none(dst_port_range.get('min_port')) or 0
        port_max = int_or_none(dst_port_range.get('max_port')) or 0
    rule_destinations = []
    if port_min == port_max == 0:
        rule_destinations.append('any')
    if port_min == port_max:
        rule_destinations.append(str(port_min))
    rule_destinations.append(f'{str(port_min)}-{str(port_max)}')

    rule_destination_match = False

    if any(rule_protocol.startswith(x) for x in PROTOCOLS):
        if 'any' in rule_destinations or str(port) in rule_destinations:
            rule_destination_match = True
        else:
            for rule_port_range in rule_destinations:
                if '-' in rule_port_range:
                    try:
                        from_port, to_port = rule_port_range.split('-')
                        if int(from_port.strip()) <= port <= int(to_port.strip()):
                            rule_destination_match = True
                            break
                    except Exception:
                        logger.exception(f'Failed parsing port range {rule_port_range!r}')

        if rule_destination_match:
            dest_rule = properties.get('src')
            return CIDR_BLOCK_ALL in dest_rule or dest_rule in PERMISSIVE_DESTINATION_RULES
    return False


def _check_inbound_nsg_list(device: OracleCloudDeviceInstance,
                            rule_section: str,
                            port: int,
                            origin=SecurityRuleOrigin.SECLIST,
                            only_default_rules=False):
    nsg_list = device.get_field_safe('nsg_rules') or []
    for nsg_rule in nsg_list:
        if is_nsg_allow_inbound_internet(nsg_rule, port, origin, only_default_rules):
            device.add_oracle_cloud_cis_incompliant_rule(rule_section)
            break


def check_api_keys(api_keys: List[OracleCloudUserApiKey]):
    if not (api_keys and isinstance(api_keys, list)):
        return False
    for api_key in api_keys:
        time_created = api_key.get_field_safe('time_created')
        days_ago_90 = parse_date(datetime.datetime.now() - datetime.timedelta(days=CIS_API_KEY_ROTATION_DAYS))
        if time_created and isinstance(time_created, datetime.datetime):
            if parse_date(time_created) < days_ago_90:
                return True
    return False


def append_oracle_cloud_cis_data_to_user(user: OracleCloudUserInstance):
    """
    Add CIS rule incompliances to Oracle Cloud users:
    1.11 mfa enabled
    1.12 api keys no older than 90 days
    1.13 admins dont have api keys
    """
    if user.get_field_safe('is_mfa_active') is False:
        user.add_oracle_cloud_cis_incompliant_rule('1.11')
    api_keys = user.get_field_safe('api_keys')
    if check_api_keys(api_keys):
        user.add_oracle_cloud_cis_incompliant_rule('1.12')
    is_admin = user.get_field_safe('is_admin')
    if is_admin and api_keys:
        user.add_oracle_cloud_cis_incompliant_rule('1.13')  # If there's any API key, then rule is violated


def append_oracle_cloud_cis_data_to_device(device: OracleCloudDeviceInstance):
    """
    Add CIS rule incompliances to Oracle Cloud instances:
    2.1 ssh from internet in security lists
    2.2 rdp from internet in security lists
    2.5 ssh from internet in default security list
    :param device: Oracle Cloud device instance
    """
    # section 2
    nsg_list = device.get_field_safe('nsg_rules')
    if nsg_list and isinstance(nsg_list, list):
        _check_inbound_nsg_list(device, '2.1', PORT_SSH)
        _check_inbound_nsg_list(device, '2.2', PORT_RDP)
        _check_inbound_nsg_list(device, '2.5', PORT_SSH, only_default_rules=True)
