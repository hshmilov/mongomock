# pylint: disable=abstract-class-instantiated
import itertools
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.azure.client import AzureCloudConnection
from axonius.clients.azure.consts import (AZURE_ACCOUNT_TAG, AZURE_CLIENT_ID,
                                          AZURE_CLIENT_SECRET,
                                          AZURE_CLOUD_ENVIRONMENT,
                                          AZURE_HTTPS_PROXY,
                                          AZURE_STACK_HUB_PROXY_SETTINGS,
                                          AZURE_STACK_HUB_RESOURCE,
                                          AZURE_STACK_HUB_URL,
                                          AZURE_SUBSCRIPTION_ID,
                                          AZURE_TENANT_ID, AZURE_VERIFY_SSL,
                                          AzureClouds,
                                          AzureStackHubProxySettings)
from axonius.mixins.configurable import Configurable
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from azure_adapter.azure_cis import append_azure_cis_data_to_device
from azure_adapter.client import AzureClient
from azure_adapter.consts import POWER_STATE_MAP
from azure_adapter.structures import (AzureDeviceInstance, AzureImage,
                                      AzureNetworkSecurityGroupRule,
                                      AzureSoftwareUpdate)

logger = logging.getLogger(f'axonius.{__name__}')


class AzureAdapter(AdapterBase, Configurable):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(AzureDeviceInstance):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        if not client_config.get('fetch_all_subscriptions'):
            return f'{client_config.get(AZURE_SUBSCRIPTION_ID)}_{client_config[AZURE_TENANT_ID]}'
        return f'all_subscriptions_for_{client_config[AZURE_TENANT_ID]}'

    def _test_reachability(self, client_config):
        raise NotImplementedError

    # pylint: disable=too-many-branches,too-many-statements,too-many-locals
    def _connect_client(self, client_config):
        """ If fetch_all_subscriptions is checked, pull all associated
        Subscriptions and create a client for each of them. If an error
        occurs, that error will be reflected to the GUI as a connection
        issue.

        I'm thinking of loading each client, metadata_dict into a list of tuples,
        then returning those at the end of the function. I'd then need to pick
        those up in _query_devices_by_client and iterate through them
        """
        azure_stack_hub_proxy_settings_value = client_config.get(AZURE_STACK_HUB_PROXY_SETTINGS)
        azure_stack_hub_proxy_settings = AzureStackHubProxySettings.ProxyOnlyAuth
        _azure_rest_client = None
        try:
            if azure_stack_hub_proxy_settings_value:
                azure_stack_hub_proxy_settings = [
                    x for x in AzureStackHubProxySettings if x.value == azure_stack_hub_proxy_settings_value][0]
        except Exception:
            logger.warning(f'Failed getting azure stack hub proxy settings. '
                           f'Original value is {str(azure_stack_hub_proxy_settings_value)}', exc_info=True)
            # fallthrough

        # Try to get all subscriptions anyway because it is always available
        try:
            cloud = {
                'Global': AzureClouds.Public,
                'China': AzureClouds.China,
                'Azure Public Cloud': AzureClouds.Public,
                'Azure China Cloud': AzureClouds.China,
                'Azure German Cloud': AzureClouds.Germany,
                'Azure US Gov Cloud': AzureClouds.Gov
            }.get(client_config.get(AZURE_CLOUD_ENVIRONMENT))

            management_url = None
            resource = None
            azure_stack_hub_proxy_settings_for_rest_client = None

            if client_config.get(AZURE_STACK_HUB_URL) and client_config.get(AZURE_STACK_HUB_RESOURCE):
                management_url = client_config[AZURE_STACK_HUB_URL]
                resource = client_config[AZURE_STACK_HUB_RESOURCE]
                azure_stack_hub_proxy_settings_for_rest_client = azure_stack_hub_proxy_settings

            with AzureCloudConnection(
                    app_client_id=client_config[AZURE_CLIENT_ID],
                    app_client_secret=client_config[AZURE_CLIENT_SECRET],
                    tenant_id=client_config[AZURE_TENANT_ID],
                    cloud=cloud,
                    management_url=management_url,
                    resource=resource,
                    azure_stack_hub_proxy_settings=azure_stack_hub_proxy_settings_for_rest_client,
                    https_proxy=client_config.get(AZURE_HTTPS_PROXY),
                    proxy_username=client_config.get('proxy_username'),
                    proxy_password=client_config.get('proxy_password'),
                    verify_ssl=client_config.get(AZURE_VERIFY_SSL)
            ) as azure_rest_client:
                _azure_rest_client = azure_rest_client
                subscriptions = azure_rest_client.all_subscriptions.copy()
        except Exception:
            subscriptions = {}
            logger.warning(f'Failed fetching subscriptions', exc_info=True)
            if client_config.get('fetch_all_subscriptions'):
                raise

        if not client_config.get('fetch_all_subscriptions'):
            c_subs_id = client_config.get(AZURE_SUBSCRIPTION_ID)
            if c_subs_id:
                subscriptions = {c_subs_id: subscriptions.get(c_subs_id) or {}}
            else:
                subscriptions = {}

        if not subscriptions:
            raise ClientConnectionException(f'Unable to find a subscription')

        connections = list()
        for subscription_idx, (subscription_id, subscription_data) in enumerate(subscriptions.items()):
            logger.info(f'Working with subscription {subscription_id}: '
                        f'({subscription_idx+1}/{len(subscriptions)})')
            try:
                connection = AzureClient(subscription_id=subscription_id,
                                         client_id=client_config[AZURE_CLIENT_ID],
                                         client_secret=client_config[AZURE_CLIENT_SECRET],
                                         tenant_id=client_config[AZURE_TENANT_ID],
                                         cloud_name=client_config.get(AZURE_CLOUD_ENVIRONMENT),
                                         azure_stack_hub_resource=client_config.get(AZURE_STACK_HUB_RESOURCE),
                                         azure_stack_hub_url=client_config.get(AZURE_STACK_HUB_URL),
                                         azure_stack_hub_proxy_settings=azure_stack_hub_proxy_settings,
                                         https_proxy=client_config.get(AZURE_HTTPS_PROXY),
                                         proxy_username=client_config.get('proxy_username'),
                                         proxy_password=client_config.get('proxy_password'),
                                         verify_ssl=client_config.get(AZURE_VERIFY_SSL))

                connection.test_connection()

                metadata_dict = dict()
                if client_config.get(AZURE_ACCOUNT_TAG):
                    metadata_dict[AZURE_ACCOUNT_TAG] = client_config.get(AZURE_ACCOUNT_TAG)
                metadata_dict['subscription'] = subscription_id
                metadata_dict['azure_client'] = _azure_rest_client
                if subscription_data and subscription_data.get('displayName'):
                    metadata_dict['subscription_name'] = subscription_data.get('displayName')
                account_id = client_config.get(AZURE_TENANT_ID) or 'unknown-tenant-id'
                metadata_dict['azure_account_id'] = account_id
                connections.append((connection, metadata_dict))

            except Exception as err:
                message = f'Error connecting to azure with subscription_id (subscription),' \
                          f' reason: {str(err)}'
                logger.exception(message)
                raise ClientConnectionException(message)

        return connections

    def _clients_schema(self):
        return {
            'items': [
                {
                    'name': AZURE_SUBSCRIPTION_ID,
                    'title': 'Azure Subscription ID',
                    'type': 'string'
                },
                {
                    'name': 'fetch_all_subscriptions',
                    'title': 'Fetch All Subscriptions',
                    'type': 'bool',
                    'default': False
                },
                {
                    'name': AZURE_CLIENT_ID,
                    'title': 'Azure Client ID',
                    'type': 'string'
                },
                {
                    'name': AZURE_CLIENT_SECRET,
                    'title': 'Azure Client Secret',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': AZURE_TENANT_ID,
                    'title': 'Azure Tenant ID',
                    'type': 'string'
                },
                {
                    'name': AZURE_CLOUD_ENVIRONMENT,
                    'title': 'Cloud Environment',
                    'type': 'string',
                    'enum': list(AzureClient.get_clouds().keys()),
                    'default': AzureClient.DEFAULT_CLOUD
                },
                {
                    'name': AZURE_STACK_HUB_URL,
                    'title': 'Azure Stack Hub Management URL',
                    'type': 'string',
                    'description': 'If you are using Azure Stack Hub, please specify the management URL'
                },
                {
                    'name': AZURE_STACK_HUB_RESOURCE,
                    'title': 'Azure Stack Hub Resource String',
                    'type': 'string',
                    'description': 'If you are using Azure Stack Hub, please specify the resource string'
                },
                {
                    'name': AZURE_STACK_HUB_PROXY_SETTINGS,
                    'title': 'Azure Stack Hub Proxy Settings',
                    'type': 'string',
                    'enum': [x.value for x in AzureStackHubProxySettings],
                    'default': AzureStackHubProxySettings.ProxyOnlyAuth.value
                },
                {
                    'name': AZURE_ACCOUNT_TAG,
                    'title': 'Account Tag',
                    'type': 'string'
                },
                {
                    'name': AZURE_VERIFY_SSL,
                    'title': 'Verify SSL',
                    'type': 'bool',
                    'default': True
                },
                {
                    'name': AZURE_HTTPS_PROXY,
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                },
                {
                    'name': 'proxy_username',
                    'title': 'HTTPS Proxy User Name',
                    'type': 'string'
                },
                {
                    'name': 'proxy_password',
                    'title': 'HTTPS Proxy Password',
                    'type': 'string',
                    'format': 'password'
                }
            ],
            'required': [
                'fetch_all_subscriptions',
                AZURE_CLIENT_ID,
                AZURE_CLIENT_SECRET,
                AZURE_TENANT_ID,
                AZURE_CLOUD_ENVIRONMENT,
                AZURE_VERIFY_SSL,
                AZURE_STACK_HUB_PROXY_SETTINGS
            ],
            'type': 'array'
        }

    @staticmethod
    def _fetch_all_software_updates(
            azure_client: AzureCloudConnection,
            raw_software_updates: dict,
            subscription_id: str
    ):
        """
        Fetch software updates only for new subscriptions where it wasn't fetched before.
        Return updated list of of these updates to be used later for other devices.

        raw_software_updates contains raw software updates in the following structure:
        {
          "subscriptionID1_resourceGroupID2":
          {
            "automation_account_1":
            {
              "name": "",
              "location": "",
              "update_plans":
              [
                {
                  "name": "update_config_1"
                  .....
                  .....
                }
              ]
            }
          }
        }

        :param azure_client:
        :param raw_software_updates: dict
        :param subscription_id: str
        :return: raw_software_updates
        """

        if not (subscription_id and isinstance(subscription_id, str)):
            raise Exception(f'Invalid subscription id: {str(subscription_id)}')

        if raw_software_updates.get(subscription_id):
            return raw_software_updates

        raw_software_updates[subscription_id] = {}

        try:
            automation_accounts = list(azure_client.automation.get_all_automation_accounts_for_subscription(
                subscription_id
            ))
        except Exception as err:
            logger.debug(
                f'Failed to fetch all automation accounts of subscription: {subscription_id} , '
                f'Error: {str(err)}',
                exc_info=True
            )
            return raw_software_updates

        for automation_account in automation_accounts:
            automation_account_name = automation_account.get('name')
            automation_account_id = automation_account.get('id')
            resource_group = automation_account_id[automation_account_id.find(
                '/resourceGroups/') + len('/resourceGroups/'):].split('/')[0]
            if not (automation_account_name and isinstance(automation_account_name, str)):
                logger.warning(
                    f'Invalid automation account name: {str(automation_account_name)} '
                    f', subscription id: {str(subscription_id)}'
                )
                continue

            # Get list of software update plans if it doesn't exist already.
            try:
                raw_updates = list(azure_client.automation.get_update_configurations(
                    subscription_id=subscription_id,
                    automation_account_name=automation_account_name,
                    resource_group=resource_group
                ))
            except Exception as exc:
                logger.debug(
                    f'Could not fetch the required software update configurations for '
                    f'subscription id: {subscription_id} ,'
                    f'automation account: {automation_account_name} ,'
                    f'resource group: {resource_group} '
                    f'Exception: {str(exc)}',
                    exc_info=True
                )
                continue

            if not isinstance(raw_updates, list):
                logger.debug(f'Invalid format of software update configurations: {str(raw_updates)[:50]}')
                continue

            raw_software_updates[subscription_id] = {
                automation_account_name:
                    {
                        'location': automation_account.get('location'),
                        'update_plans': raw_updates
                    }
            }

        return raw_software_updates

    def _parse_software_updates(self, device: MyDeviceAdapter, raw_software_updates):
        subscription_id = device.subscription_id
        resource_group = device.resources_group
        machine_id = device.id

        if not isinstance(subscription_id, str):
            raise TypeError(f'Unexpected type of subscription id: {str(type(subscription_id))}')
        if not isinstance(resource_group, str):
            raise TypeError(f'Unexpected type of resource group: {str(type(resource_group))}')
        if not isinstance(machine_id, str):
            raise TypeError(f'Unexpected type of machine id: {str(type(machine_id))}')

        for subscription_resource_group in raw_software_updates:
            automation_accounts = raw_software_updates.get(subscription_resource_group)
            for automation_account_name in automation_accounts:
                automation_account = automation_accounts.get(automation_account_name)
                raw_update_plans = automation_account.get('update_plans')
                for raw_update_plan in raw_update_plans:
                    properties = raw_update_plan.get('properties', {})
                    update_configuration = properties.get('updateConfiguration', {})
                    if self._is_relevant_software_update(device, update_configuration):
                        device.software_updates.append(
                            AzureSoftwareUpdate(
                                name=raw_update_plan.get('name'),
                                id=raw_update_plan.get('id'),
                                automation_account_name=automation_account_name,
                                location=automation_account.get('location'),
                                operating_system=update_configuration.get('operatingSystem'),
                                duration=update_configuration.get('duration'),
                                frequency=properties.get('frequency'),
                                provisioning_state=properties.get('provisioningState'),
                                start_time=parse_date(properties.get('startTime')),
                                creation_time=parse_date(properties.get('creationTime')),
                                last_modified_time=parse_date(properties.get('lastModifiedTime')),
                                next_run=parse_date(properties.get('nextRun'))
                            )
                        )

    @staticmethod
    # pylint: disable=W0640
    def _is_relevant_software_update(device: MyDeviceAdapter, raw_update_configurations: dict):
        azure_queries = raw_update_configurations.get('targets', {}).get('azureQueries', [])

        for azure_query in azure_queries:
            device_os = device.get_field_safe('os') or device.get_field_safe('os_guess')
            device_os_type = device_os.get_field_safe('type').lower() or ''
            resource_group_identifier = f'/subscriptions/{device.subscription_id}' \
                                        f'/resourceGroups/{device.resources_group}'.lower()

            scope = azure_query.get('scope', [])
            if isinstance(scope, str):
                logger.debug(f'Unexpected type for scope: {scope}')
                scope = []
            scope = [s.lower() for s in scope]
            locations = azure_query.get('locations', [])
            tags = azure_query.get('tagSettings', {}).get('tags', {})
            filter_operator = azure_query.get('tagSettings', {}).get('filterOperator', '').lower()
            update_target_os = raw_update_configurations.get('operatingSystem', '').lower()

            if update_target_os and update_target_os != device_os_type:
                continue
            if scope and resource_group_identifier not in scope:
                continue
            if locations and device.location not in locations:
                continue

            def has_tag(tag):
                return tag in tags
            if tags and filter_operator == 'any':
                if not any(has_tag(dev_tag) for dev_tag in device.tags):
                    continue
            if tags and filter_operator == 'all':
                if not all(has_tag(dev_tag) for dev_tag in device.tags):
                    continue

            return True
        return False

    # pylint: disable=arguments-differ
    def _query_devices_by_client(self, client_name, client_data_all):
        for connection in client_data_all:
            try:
                (client_data, metadata) = connection
            except Exception:
                logger.exception(f'Failed to process a connection: {str(connection)}')
                continue

            subscription_id = metadata.get('subscription')
            logger.info(f'Querying vms for subscription {subscription_id}')
            try:
                yield client_data.get_virtual_machines(), metadata
            except Exception as e:
                logger.exception(f'Failed to query VMs for subscription {metadata.get("subscription")}: {str(e)}')
                continue

        logger.info(f'Finished querying all connections')

    # pylint: disable=arguments-differ,too-many-nested-blocks,too-many-branches,too-many-statements,too-many-locals, inconsistent-return-statements
    def _parse_raw_data(self, devices_raw_data_all):
        raw_software_updates = {}

        for devices_raw_data, metadata in devices_raw_data_all:
            for device_raw in devices_raw_data:
                device = self._new_device_adapter()
                device_id = device_raw['id']
                device.id = device_id
                device.resources_group = None
                if device_id and '/resourceGroups/' in device_id:
                    device.resources_group = device_id[device_id.find('/resourceGroups/') +
                                                       len('/resourceGroups/'):].split('/')[0]
                device.cloud_provider = 'Azure'
                device.name = device_raw['name']
                device.location = device_raw.get('location')
                device.instance_type = device_raw.get('hardware_profile', {}).get('vm_size')
                image = device_raw.get('storage_profile', {}).get('image_reference')
                os_disk = device_raw.get('storage_profile', {}).get('os_disk')
                tags = device_raw.get('tags') or {}

                if tags:
                    try:
                        for tag_name, tag_value in tags.items():
                            device.add_key_value_tag(tag_name, tag_value)
                    except Exception:
                        logger.exception(f'Could not get tags')

                os_info = []
                if os_disk is not None:
                    # Add the OS's HD as a hard-drive
                    device.add_hd(total_size=os_disk.get('disk_size_gb'))
                    os_info.append(os_disk.get('os_type'))
                if image is not None:
                    image_id = image.get('id')
                    if image_id and '/images/' in image_id:
                        device.custom_image_name = image_id[image_id.find('/images/') + len('/images/'):].split('/')[0]
                    device.image = AzureImage(publisher=image.get('publisher'),
                                              offer=image.get('offer'),
                                              sku=image.get('sku'),
                                              version=image.get('version'),
                                              exact_version=image.get('exact_version'))
                    os_info.extend([image.get('offer'), image.get('sku'), image.get('exact_version')])
                instance_view = device_raw.get('instance_view')
                if instance_view and isinstance(instance_view, dict):
                    if instance_view.get('os_name'):
                        os_info.append(str(instance_view.get('os_name')))
                    if instance_view.get('os_version'):
                        os_info.append(str(instance_view.get('os_version')))
                device.figure_os(' '.join([v for v in os_info if v is not None]))
                for disk in device_raw.get('storage_profile', {}).get('data_disks', []):
                    # add also the attached HDs
                    device.add_hd(total_size=disk.get('disk_size_gb'))
                device.hostname = device_raw.get('os_profile', {}).get('computer_name')
                device.admin_username = device_raw.get('os_profile', {}).get('admin_username')
                device.vm_id = device_raw.get('vm_id')
                device.cloud_id = device_raw.get('vm_id')
                for iface in device_raw.get('network_profile', {}).get('network_interfaces', []):
                    ips = []
                    subnets = []
                    for ip_config in iface.get('ip_configurations', []):
                        private_ip = ip_config.get('private_ip_address')
                        if private_ip:
                            ips.append(private_ip)
                        public_ip = ip_config.get('public_ip_address', {}).get('ip_address')
                        if public_ip:
                            ips.append(public_ip)
                            device.add_public_ip(public_ip)
                        subnets.append(ip_config.get('subnet', {}).get('address_prefix'))
                        subnet_id = ip_config.get('subnet', {}).get('id')
                        if subnet_id and '/virtualNetworks/' in subnet_id:
                            device.virtual_networks.append(subnet_id[subnet_id.find('/virtualNetworks/') +
                                                                     len('/virtualNetworks/'):].split('/')[0])
                    device.add_nic(mac=iface.get('mac_address'), ips=[ip for ip in ips if ip is not None],
                                   subnets=[subnet for subnet in subnets if subnet is not None], name=iface.get('name'))

                    try:
                        nsg = iface.get('network_security_group') or {}
                        if not nsg:
                            device.firewall_rules = []
                            device.azure_firewall_rules = []
                        else:
                            for rule, is_default in itertools.chain(
                                    zip(nsg.get('security_rules') or [], itertools.repeat(False)),
                                    zip(nsg.get('default_security_rules') or [], itertools.repeat(True))
                            ):
                                access = rule.get('access')
                                description = rule.get('description')
                                direction = rule.get('direction')
                                rule_id = rule.get('id')
                                name = rule.get('name')
                                priority = rule.get('Priority')
                                protocol = rule.get('protocol')
                                destination_address_prefix = rule.get('destination_address_prefix')
                                destination_address_prefixes = rule.get('destination_address_prefixes') or []
                                if destination_address_prefix:
                                    destination_address_prefixes.append(destination_address_prefix)
                                destination_port_range = rule.get('destination_port_range')
                                destination_port_ranges = rule.get('destination_port_ranges') or []
                                if destination_port_range:
                                    destination_port_ranges.append(destination_port_range)

                                source_address_prefix = rule.get('source_address_prefix')
                                source_address_prefixes = rule.get('source_address_prefixes') or []
                                if source_address_prefix:
                                    source_address_prefixes.append(source_address_prefix)
                                source_port_range = rule.get('source_port_range')
                                source_port_ranges = rule.get('source_port_ranges') or []
                                if source_port_range:
                                    source_port_ranges.append(source_port_range)

                                iface_name = iface.get('name')

                                # First, build the specific rule
                                rule = AzureNetworkSecurityGroupRule(
                                    iface_name=iface_name,
                                    access=access,
                                    description=description,
                                    direction=direction,
                                    rule_id=rule_id,
                                    name=name,
                                    priority=priority,
                                    protocol=protocol,
                                    source_address_prefixes=source_address_prefixes,
                                    source_port_ranges=source_port_ranges,
                                    destination_address_prefixes=destination_address_prefixes,
                                    destination_port_ranges=destination_port_ranges,
                                    is_default=is_default
                                )
                                device.azure_firewall_rules.append(rule)

                                # Next, parse the generic rule.
                                # If that is an inbound rule, we care about the
                                # source prefix, but destination port.
                                # If that is an outbound rule, we care about the
                                # destination prefix, and destination port.
                                port_ranges_to_check = destination_port_ranges
                                if str(direction).lower() == 'inbound':
                                    fw_direction = 'INGRESS'
                                    address_prefixes_to_check = source_address_prefixes
                                elif str(direction).lower() == 'outbound':
                                    fw_direction = 'EGRESS'
                                    address_prefixes_to_check = destination_address_prefixes
                                else:
                                    logger.error(f'Found unknown direction {str(direction)}, bypassing')
                                    continue

                                for address_prefix in address_prefixes_to_check:
                                    for port_range in port_ranges_to_check:
                                        if port_range == '*' or str(port_range).lower() == 'all' or \
                                                str(port_range).lower() == 'any':
                                            from_port = 0
                                            to_port = 65535
                                        elif '-' in port_range:
                                            try:
                                                from_port, to_port = port_range.split('-')
                                            except Exception:
                                                from_port, to_port = None, None
                                        else:
                                            try:
                                                from_port, to_port = port_range, port_range
                                            except Exception:
                                                from_port, to_port = None, None

                                        if address_prefix == '*':
                                            address_prefix = '0.0.0.0/0'

                                        if protocol == '*' or str(protocol).lower() == 'all' \
                                                or str(protocol).lower() == 'any':
                                            protocol = 'Any'

                                        device.add_firewall_rule(
                                            name=f'{name} (iface {iface_name})',
                                            source='Azure NIC network security group',
                                            type='Allow' if str(access).lower() == 'allow' else 'Deny',
                                            direction=fw_direction,
                                            target=address_prefix,
                                            protocol=protocol,
                                            from_port=from_port,
                                            to_port=to_port
                                        )

                    except Exception:
                        logger.exception(f'Failed to parse network security group, continuing')
                self._fill_power_state(device, device_raw)

                device.account_tag = metadata.get(AZURE_ACCOUNT_TAG)
                device.subscription_name = metadata.get('subscription_name')
                device.subscription_id = metadata.get('subscription')
                device.software_updates = []
                azure_client = metadata.get('azure_client')
                try:
                    if self._fetch_update_deployments:
                        raw_software_updates = self._fetch_all_software_updates(
                            azure_client=azure_client,
                            raw_software_updates=raw_software_updates,
                            subscription_id=device.subscription_id
                        )
                        self._parse_software_updates(device, raw_software_updates)
                except Exception as error:
                    logger.warning(f'Error occurred while fetching software updates, error:{str(error)}', exc_info=True)

                device.azure_account_id = metadata.get('azure_account_id')

                device.set_raw(device_raw)
                try:
                    device.azure_cis_incompliant = []  # Remove old rules which may be irrelevant now
                    if self.should_cloud_compliance_run():
                        append_azure_cis_data_to_device(device)
                except Exception as e:
                    logger.debug(f'Failed to add cis data to device: {str(e)}', exc_info=True)
                yield device

    @staticmethod
    def _fill_power_state(device, device_raw):
        try:
            statuses = (device_raw.get('instance_view') or {}).get('statuses') or []
            if statuses:
                power_states = list(filter(lambda status: status.get('code', '').startswith('PowerState'), statuses))
                if len(power_states) == 0:
                    logger.warning(f'Failed locating power_state for {device.id}, statuses: {statuses}')
                    return

                if len(power_states) > 1:
                    logger.warning(f'Multiple power states located for device {device.id},'
                                   f' taking the first from {power_states}')
                    # fallthrough

                power_state_str = power_states[0].get('code', '')
                power_state = POWER_STATE_MAP.get(power_state_str)
                if not power_state:
                    logger.error(f'Unknown power state value located "{power_state_str}" for {device.id}')
                    return

                device.power_state = power_state
        except Exception:
            logger.exception('Failed parsing vm power state, continue')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.Cloud_Provider]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'fetch_update_deployments',
                    'title': 'Fetch update deployments',
                    'type': 'bool'
                }
            ],
            'required': [
                'fetch_update_deployments'
            ],
            'pretty_name': 'Azure Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'fetch_update_deployments': False
        }

    def _on_config_update(self, config):
        self._fetch_update_deployments = config['fetch_update_deployments']
