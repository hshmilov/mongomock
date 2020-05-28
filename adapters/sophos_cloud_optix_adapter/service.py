""" This module supports data processing for the Sophos Cloud Optix service. """
# pylint: disable=logging-format-interpolation,import-error,too-few-public-methods
import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field, ListField
from axonius.mixins.configurable import Configurable
from axonius.users.user_adapter import UserAdapter
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.json import from_json
from axonius.utils.parsing import figure_out_cloud
from sophos_cloud_optix_adapter.client_id import get_client_id
from sophos_cloud_optix_adapter.connection import SophosCloudOptixConnection
from sophos_cloud_optix_adapter.structures import (GCPServiceAccount,
                                                   AzureGCPIpConfiguration,
                                                   AzureGCPNetworkInterface,
                                                   SecurityGroup)

logger = logging.getLogger(f'axonius.{__name__}')


class SophosCloudOptixAdapter(AdapterBase, Configurable):
    """ The parameters defined below contain the common fields for each
    cloud provider service (i.e. AWS, Azure and GCP) along with fields
    that are specific to each of those providers.
    """
    class MyDeviceAdapter(DeviceAdapter):
        """ This is only to make pylint happy. We all know what this
        class does.
        """
        # pylint: disable=too-many-instance-attributes
        account_id = Field(str, 'Account ID')
        availability_zone = Field(str, 'Availability Zone')
        can_ip_forward = Field(bool, 'Can IP Forward')
        cpu_platform = Field(str, 'CPU Platform')
        data_disk_encryption = Field(bool, 'Data Disk Encryption')
        deletion_protection = Field(bool, 'Deletion Protection')
        has_container_nodes = Field(bool, 'Has Container Nodes')
        image_id = Field(str, 'Image ID')
        instance_profile_id = Field(str, 'Instance Profile ID')
        instance_type = Field(str, 'Instance Type')
        is_iam_role_assigned = Field(bool, 'IAM Role Assigned')
        is_public = Field(bool, 'Is Public')
        kind = Field(str, 'Kind')
        last_modified_by = Field(str, 'Last Modified By')
        nic = ListField(AzureGCPNetworkInterface, 'Network Interface')
        nsg_id = Field(str, 'Network Security Group ID')
        os_disk_encryption = Field(bool, 'OS Disk Encryption')
        password_login = Field(bool, 'Password Login')
        primary_security_group = Field(str, 'Primary Security Group')
        private_ip = Field(str, 'Private IP')
        provisioning_state = Field(str, 'Provisioning State')
        public_ip = Field(str, 'Public IP')
        region = Field(str, 'Region')
        resource_group = Field(str, 'Resource Group')
        security_groups = ListField(SecurityGroup, 'Security Groups')
        service_accounts = ListField(GCPServiceAccount, 'Service Accounts')
        start_restricted = Field(bool, 'Start Restricted')
        status = Field(str, 'Status')
        subnet_id = Field(str, 'Subnet ID')
        vm_scale_set = Field(str, 'Scale Set')
        vm_scale_set_id = Field(str, 'Scale Set ID')
        vnet_id = Field(str, 'VNet ID')
        vpc_id = Field(str, 'VPC ID')
        zone = Field(str, 'Zone')

    class MyUserAdapter(UserAdapter):
        """
        SCO URI: https://optix.sophos.com/apiDocumentation#user
        GCP URI: https://developers.google.com/admin-sdk/directory/v1/reference/users
        """
        # pylint: disable=too-many-instance-attributes
        # aws and common fields
        account_id = Field(str, 'Account ID')
        access_key_age = Field(str, 'Access Key Age')
        arn = Field(str, 'ARN')
        attached_managed_policy_count = Field(int, 'Attached Managed Policy Count')
        cloud_provider = Field(str, 'Cloud Provider')
        console_passwd_status = Field(str, 'Console Password Status')
        is_active = Field(bool, 'Is User Active')
        is_mfa_active = Field(bool, 'Is MFA Active')
        is_over_privileged = Field(bool, 'Is User Over-Privileged')
        last_modified_by = Field(str, 'Last Modified By')
        password_last_changed = Field(datetime.datetime, 'Password Last Changed')
        password_last_used = Field(datetime.datetime, 'Password Last Used')
        path = Field(str, 'Path')
        policies_attached = ListField(str, 'Polices Attached')
        policy_utilization_ratio = Field(str, 'Policy Utilization Ratio')
        user_id = Field(str, 'User ID')
        policy_count = Field(int, 'User Policy Count')

        # gcp-specific
        agreed_to_terms = Field(bool, 'Agreed to Terms')
        change_passwd_next_login = Field(bool, 'Change Password at Next Login')
        deletion_time = Field(str, 'Deletion Date')
        ip_whitelisted = Field(bool, 'IP Whitelisted')
        is_archived = Field(bool, 'Is Archived')
        is_delegated_admin = Field(bool, 'Is Delegated Admin')
        is_enrolled_in_2sv = Field(bool, 'Is Enrolled in 2-Step Verification')
        is_enforced_in_2sv = Field(bool, 'Is 2-Step Verification Enforced')
        is_suspended = Field(bool, 'Is Suspended')
        last_login = Field(str, 'Last Login')
        org_id = Field(str, 'Organization ID')
        primary_email = Field(str, 'Primary Email')

        # azure-specific
        nickname = Field(str, 'Nickname')
        principal_name = Field(str, 'Principal Name')
        signin_name = Field(str, 'Sign-In Name')
        source = Field(str, 'Source')
        tenant_id = Field(str, 'Tenant ID')
        usage_location = Field(str, 'Usage Location')
        user_type = Field(str, 'User Type')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(host=client_config.get('domain'),
                                                https_proxy=client_config.get('https_proxy'))

    def _get_providers(self) -> dict:
        """ Determine which cloud providers to query (all are enabled in
        the GUI by default. A dict is returned to the caller."""
        providers = {
            'AWS': self.__fetch_aws,
            'Azure': self.__fetch_azure,
            'GCP': self.__fetch_gcp,
        }
        return providers

    def get_connection(self, client_config):
        """ Gets an authenticated connection from connection.py """
        connection = SophosCloudOptixConnection(domain=client_config.get('domain'),
                                                verify_ssl=client_config.get('verify_ssl'),
                                                https_proxy=client_config.get('https_proxy'),
                                                apikey=client_config.get('apikey'),
                                                providers=self._get_providers())
        with connection:
            pass
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as err:
            message = f'Error connecting to client with domain ' \
                      f'{client_config["domain"]}, reason: {str(err)}'
            logger.exception(message)
            raise ClientConnectionException(message)

    @staticmethod
    def _query_devices_by_client(client_name, client_data):
        """
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_device_list()

    # pylint: disable=unused-argument, arguments-differ
    @staticmethod
    def _query_users_by_client(client_name, client_data):
        """
         Get all devices from a specific  domain

         :param str client_name: The name of the client
         :param obj client_data: The data that represent a connection

         :return: A json with all the attributes returned from the Server
         """
        with client_data:
            yield from client_data.get_user_list()

    @staticmethod
    def _clients_schema():
        """
        The schema a Sophos Cloud Optix Adapter expects from the GUI.

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Hostname or IP Address',
                    'type': 'string'
                },
                {
                    'name': 'apikey',
                    'title': 'API Key',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'verify_ssl',
                    'title': 'Verify SSL',
                    'type': 'bool'
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                }
            ],
            'required': [
                'domain',
                'apikey',
                'aws',
                'azure',
                'gcp',
                'verify_ssl'
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-locals,too-many-branches,too-many-statements,too-many-nested-blocks
    def _create_device(self, device_raw):
        """ This function contains all of the possible data from all 3
        cloud service providers. Some values will be populated, while
        others will not, depending upon support for that data at the
        cloud provider.

        :param dict device_raw: A JSON collection of data that represents
        a single device in the endpoint.
        :returns device: An instance of MyDeviceAdapter, populated with
        data about that device.
        """
        try:
            device = self._new_device_adapter()
            cloud_provider = figure_out_cloud(device_raw.get('accountType'))
            device.cloud_provider = cloud_provider
            device.account_id = device_raw.get('accountId')

            device_id = device_raw.get('instanceId')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('accountId') or '')
            device.cloud_id = device_id

            more_info = device_raw.get('moreInfo') or {}

            if more_info:
                device.name = more_info.get('name')
                device.hostname = more_info.get('name')
                device.description = more_info.get('description')
                device.image_id = more_info.get('imageId')
                device.instance_profile_id = more_info.get('instanceProfileId')
                device.instance_type = more_info.get('instanceType')
                device.is_iam_role_assigned = more_info.get('isIAMRoleAssigned')
                try:
                    device.power_state = more_info.get('runningState') or \
                        more_info.get('status') or \
                        more_info.get('provisioningState')
                except Exception:
                    logger.exception(f'Failed parsing power state for device {device_raw}')
                device.figure_os(device_raw.get('osType'))
                device.resource_group = more_info.get('resourceGroup')
                device.password_login = more_info.get('passwordLogin')
                device.os_disk_encryption = more_info.get('osDiskEncryption')
                device.data_disk_encryption = more_info.get('dataDisksEncryption')
                device.zone = more_info.get('zone')
                device.region = more_info.get('region')
                device.availability_zone = more_info.get('availabilityZone')
                device.subnet_id = more_info.get('subnetId')
                device.vpc_id = more_info.get('vpcId')
                device.vnet_id = more_info.get('vnetId')
                device.is_public = more_info.get('isPublic')
                device.add_public_ip(more_info.get('publicIP'))
                device.add_ips_and_macs(ips=[more_info.get('privateIP')])
                device.has_container_nodes = more_info.get(
                    'hasContainerNodes')
                device.can_ip_forward = more_info.get('canIpForward')
                device.cpu_platform = more_info.get('cpuPlatform')
                device.kind = more_info.get('kind')
                device.start_restricted = more_info.get('startRestricted')
                device.deletion_protection = more_info.get('deletionProtection')
                device.last_modified_by = more_info.get('lastModifiedBy')
                device.primary_security_group = more_info.get('primarySecurityGroup')

                # firewalls: aws and azure
                try:
                    security_group_list = list()
                    sec_groups = more_info.get('securityGroupList')
                    if sec_groups and isinstance(sec_groups, list):
                        for sec_group in sec_groups:
                            security_group_list.append(SecurityGroup(
                                key=sec_group.get('name'),
                                value=sec_group.get('value')))
                        device.security_groups = security_group_list
                except Exception as err:
                    logger.exception(f'Unable to create security groups for '
                                     f'{device_raw} on {cloud_provider}: {err}')

                # firewalls: gcp
                try:
                    security_group_list = list()
                    sec_groups = more_info.get('firewallList')
                    if sec_groups and isinstance(sec_groups, list):
                        for sec_group in sec_groups:
                            try:
                                security_group_list.append(sec_group)
                                device.security_groups = security_group_list
                            except Exception as err:
                                logger.exception(f'Unable to create a firewall in {device_raw}: {err}')
                except Exception as err:
                    logger.exception(f'Unable to populate the firewall list for '
                                     f'{device_raw} on {cloud_provider}: {err}')

                # nics: aws and azure
                for nic in (more_info.get('networkInterfaces') or []):
                    try:
                        private_ips = set()
                        private_ip = nic.get('privateIP')
                        if isinstance(private_ip, list):
                            private_ips.update(private_ip)
                        elif isinstance(private_ip, str):
                            private_ips.add(private_ip)
                        else:
                            logger.exception(f'Wrong data type for private_ip in {device_raw}')

                        public_ips = set()
                        public_ip = nic.get('publicIP')
                        if isinstance(public_ip, list):
                            public_ips.update(public_ip)
                        elif isinstance(public_ip, str):
                            public_ips.add(public_ip)
                        else:
                            logger.exception(f'Wrong data type for public_ip in {device_raw}')

                        netif = AzureGCPNetworkInterface(id=nic.get('interfaceId'),
                                                         name=nic.get('name') or nic.get('interfaceId'),
                                                         public_ip=list(public_ips),
                                                         private_ip=list(private_ips),
                                                         sec_group_id=nic.get('nsgId')
                                                         )
                        # there is a potential typo in the docs, so testing for the [sic] and correct spelling
                        if isinstance(nic.get('ipConfigration'), list) or \
                                isinstance(nic.get('ipConfiguration'), list):
                            for configuration in (nic.get('ipConfigration') or
                                                  nic.get('ipConfiguration')):
                                config_public_ip = configuration.get('publicIP')
                                if isinstance(config_public_ip, list):
                                    public_ips.update(config_public_ip)
                                else:
                                    public_ips.add(config_public_ip)

                                config_private_ip = configuration.get('privateIP')
                                if isinstance(config_private_ip, list):
                                    private_ips.update(config_private_ip)
                                else:
                                    private_ips.add(config_private_ip)

                                config = AzureGCPIpConfiguration(name=configuration.get('name'),
                                                                 private_ip=list(private_ips),
                                                                 public_ip=list(public_ips),
                                                                 subnet=configuration.get('subnet'),
                                                                 is_primary=configuration.get('primary'),
                                                                 app_sec_groups=configuration
                                                                 .get('applicationSecurityGroups')
                                                                 )

                                netif.ip_configuration.append(config)

                            netif.ips = list(private_ips.union(public_ips))
                            device.add_nic(name=netif.name, ips=netif.ips)

                        device.nic.append(netif)

                    except Exception as err:
                        logger.exception(f'Problem creating network interface for'
                                         f' {nic} on {cloud_provider}: {err}')

                # nics: gcp
                for nic in (more_info.get('networkInterfaceList') or []):
                    try:
                        private_ips = set()
                        private_ip = nic.get('privateIp')
                        if isinstance(private_ip, list):
                            private_ips.update(private_ip)
                        elif isinstance(private_ip, str):
                            private_ips.add(private_ip)
                        else:
                            logger.exception(f'Wrong data type for private_ip in {device_raw}')

                        ips = list(private_ips)

                        netif = AzureGCPNetworkInterface(name=nic.get('name'),
                                                         private_ip=list(private_ips),
                                                         ips=ips,
                                                         network_id=nic.get('networkId'),
                                                         subnet_id=nic.get('subnetId'),
                                                         kind=nic.get('kind')
                                                         )
                        if isinstance(nic.get('accessConfigList'), list):
                            for configuration in nic.get('accessConfigList'):
                                config = AzureGCPIpConfiguration(name=configuration.get('name'),
                                                                 nat_ip=configuration.get('natIP'),
                                                                 public_ptr_domain_name=configuration
                                                                 .get('publicPtrDomainName'),
                                                                 kind=configuration.get('kind')
                                                                 )

                                netif.access_config.append(config)

                            device.add_nic(name=netif.name, ips=netif.ips)

                        device.nic.append(netif)

                    except Exception as err:
                        logger.exception(
                            f'Problem creating network interface for {nic} '
                            f'on {cloud_provider}: {err}')

                # drives: gcp
                for disk in (more_info.get('disksList') or []):
                    try:
                        device.add_hd(name=disk.get('name'),
                                      source_image=disk.get('sourceImage'),
                                      total_size=disk.get('diskSizeGb'),
                                      disk_type=disk.get('diskType'),
                                      other_type=disk.get('type'),
                                      mode=disk.get('mode'),
                                      source=disk.get('source'),
                                      disk_index=disk.get('index'),
                                      is_encrypted=disk.get('isEncrypted'))
                    except Exception as err:
                        logger.exception(f'Unable to populate disk drive for {disk} '
                                         f'on {cloud_provider}: {err}')

                # tags
                try:
                    if isinstance(more_info.get('tags'), dict):
                        tags = more_info.get('tags').items()
                        for key, value in tags:
                            device.add_key_value_tag(key=key, value=value)
                except Exception as err:
                    logger.exception(f'Unable to set tags for {device_raw} '
                                     f'on {cloud_provider}: {err}')

                # service accounts: gcp
                try:
                    service_accounts_list = list()
                    service_accounts = more_info.get('serviceAccountList')
                    if isinstance(service_accounts, list):
                        for svc_acct in service_accounts:
                            service_accounts_list.append(
                                GCPServiceAccount(email=svc_acct.get('email'),
                                                  scopes=svc_acct.get('scopes')))
                        device.service_accounts = service_accounts_list
                except Exception as err:
                    logger.exception(f'Unable to set service accounts for '
                                     f'{device_raw} on {cloud_provider}: {err}')

            device.set_raw(device_raw)
            return device
        except Exception as err:
            logger.exception(
                f'Problem with fetching Sophos Cloud Optix Device for '
                f'{device_raw}: {err}')

            return None

    def _create_user(self, user_raw):
        try:
            user = self._new_user_adapter()
            more_info = user_raw.get('moreInfo') or {}

            if more_info:
                user.agreed_to_terms = more_info.get('agreedToTerms')
                user.access_key_age = more_info.get('accessKeyAge')
                user.account_disabled = more_info.get('isArchived') or \
                    more_info.get('isSuspended')
                user.account_id = user_raw.get('accountId')

                try:
                    account_type = more_info.get('accountType')
                    if isinstance(account_type, str):
                        if account_type.upper() == 'AWS':
                            user.arn = more_info.get('arn')
                            if user.arn and isinstance(user.arn, str):
                                user.username = user.arn.split('/')[-1]
                            else:
                                user.username = more_info.get('userId') or ''
                        elif account_type.upper() == 'GCP':
                            user.username = more_info.get('primaryEmail') or ''
                        elif account_type.upper() == 'AZURE':
                            user.username = more_info.get('signInName') or \
                                more_info.get('mainNickname') or \
                                more_info.get('principalName') or ''
                except Exception:
                    logger.exception(f'Unable to set username: {user_raw}')

                try:
                    policy_count = more_info.get('attachedManagedPolicyCount')
                    if isinstance(policy_count, (int, str)):
                        user.attached_managed_policy_count = int(policy_count)
                except BaseException:
                    logger.warning(f'Unable to set the policy count: {user_raw}')

                try:
                    # for some reason attachedPolicies are brought as an str representation of a list
                    user.policies_attached = from_json(more_info.get('attachedPolicies'))
                except Exception:
                    logger.warning(f'Failed parsing policies attached {more_info.get("attachedPolicies")}')
                user.change_passwd_next_login = more_info.get('changePasswordAtNextLogin')
                user.console_passwd_status = more_info.get('consolePasswdStatus')
                user.cloud_provider = figure_out_cloud(user_raw.get('accountType'))
                user.deletion_time = parse_date(more_info.get('deletionTime')) or \
                    parse_date(more_info.get('deletionTimestamp'))
                groups = more_info.get('groupList')
                if isinstance(groups, str):
                    user.groups = groups.split(',')
                elif isinstance(groups, list):
                    user.groups = groups
                else:
                    logger.warning(f'Invalid type for groupList: {user_raw}')
                user.ip_whitelisted = more_info.get('ipWhitelisted')
                user.is_active = more_info.get('isActive')
                user.is_admin = more_info.get('isAdmin')
                user.is_delegated_admin = more_info.get('isDelegatedAdmin')
                user.is_enrolled_in_2sv = more_info.get('isEnrolledIn2Sv')
                user.is_enforced_in_2sv = more_info.get('isEnforcedIn2Sv')
                user.is_mfa_active = more_info.get('isMfaActive')

                over_privd = more_info.get('isOverPrivileged')
                if isinstance(over_privd, str):
                    user.is_over_privileged = over_privd.lower() == 'true'
                elif isinstance(over_privd, (bool, int)):
                    user.is_over_privileged = bool(over_privd)
                else:
                    logger.warning(f'Unable to set user is privileged status: {over_privd}')

                user.last_modified_by = more_info.get('lastModifiedBy')
                user.last_password_change = parse_date(more_info
                                                       .get('passwordLastChanged'))
                user.last_seen = parse_date(more_info.get('lastActivity')) or \
                    parse_date(more_info.get('lastLoginTime'))
                user.last_logon = parse_date(more_info.get('lastActivity')) or \
                    parse_date(more_info.get('lastLoginTime'))
                user.mail = more_info.get('primaryEmail') or more_info.get('mail')
                user.nickname = more_info.get('mainNickname')
                user.organizational_unit = more_info.get('orgId')
                user.password_last_used = parse_date((more_info.get('passwordLastUsed')))
                user.path = more_info.get('path')

                try:
                    num_policies = more_info.get('userPolicyCount')
                    if isinstance(num_policies, int):
                        user.policy_count = num_policies
                    elif isinstance(num_policies, str):
                        user.policy_count = int(num_policies)
                except BaseException:
                    logger.warning(f'Invalid data type for userPolicyCount: '
                                   f'{user_raw}')

                user.policy_utilization_ratio = more_info.get('policyUtilizationRatio')
                user.principal_name = more_info.get('principalName')
                user.source = more_info.get('source')
                user.tenant_id = more_info.get('tenantId')
                user.usage_location = more_info.get('usageLocation')
                user.user_created = parse_date(more_info.get('createDate')) or \
                    parse_date((more_info.get('creationTime')))
                user.user_type = more_info.get('userType')

                user_id = more_info.get('userId') or \
                    more_info.get('instanceId')
                if user_id is None:
                    logger.warning(f'Bad user object with no ID {user_raw}')
                    return None
                user.id = user_id + '_' + (user_raw.get('accountId') or '')

                user.set_raw(user_raw)
                return user
        except Exception as err:
            logger.exception(
                f'Problem with fetching Sophos Cloud Optix User: {err} '
                f' for user_raw: {user_raw}')
        return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    def _parse_users_raw_data(self, users_raw_data):
        for user_raw in users_raw_data:
            user = self._create_user(user_raw)
            if user:
                yield user

    @classmethod
    def adapter_properties(cls):
        """ Set the adapter properties. """
        return [AdapterProperty.Assets, AdapterProperty.UserManagement]

    def _on_config_update(self, config):
        logger.info(f'Loading Sophos config: {config}')
        self.__options = config
        self.__fetch_aws = config.get('aws') or True
        self.__fetch_azure = config.get('azure') or True
        self.__fetch_gcp = config.get('gcp') or True

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'aws',
                    'title': 'Gather from AWS',
                    'type': 'bool',
                    'default': True
                },
                {
                    'name': 'azure',
                    'title': 'Gather from Azure',
                    'type': 'bool',
                    'default': True
                },
                {
                    'name': 'gcp',
                    'title': 'Gather from GCP',
                    'type': 'bool',
                    'default': True
                },
            ],
            'required': [
                'aws',
                'azure',
                'gcp',
            ],
            'pretty_name': 'Sophos Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'aws': True,
            'azure': True,
            'gcp': True,
        }
