from mockingbird.commons.mock_network_device import MockNetworkDevice, MockNetworkDeviceProperties
from mockingbird.commons.mock_network_user import MockNetworkUser, MockNetworkUserProperties
from mockingbird.commons.adapter_parser import AdapterParser
from mockingbird.commons import mock_utils
from active_directory_adapter.service import ActiveDirectoryAdapter


class AdAdapterParser(AdapterParser):
    def __init__(self):
        super().__init__(
            ActiveDirectoryAdapter,
            [MockNetworkDeviceProperties.ADDevice], [MockNetworkUserProperties.ADUser]
        )

    @staticmethod
    def new_device_adapter() -> ActiveDirectoryAdapter.MyDeviceAdapter:
        return ActiveDirectoryAdapter.MyDeviceAdapter(set(), set())

    @staticmethod
    def new_user_adapter() -> ActiveDirectoryAdapter.MyUserAdapter:
        return ActiveDirectoryAdapter.MyUserAdapter(set(), set())

    @staticmethod
    def _parse_device(device: ActiveDirectoryAdapter.MyDeviceAdapter, network_device: MockNetworkDevice):
        org_to_ad_format = ','.join(f'DC={org_part}' for org_part in network_device.domain.split('.'))
        ou = 'Domain Controllers' if device.ad_is_dc is True else 'Computers'
        device.id = f'CN={network_device.hostname},OU={ou},{org_to_ad_format}'
        device.name = network_device.hostname.upper()
        device.hostname = f'{device.name}.{network_device.domain.upper()}'
        device.os = network_device.os
        device.domain = network_device.domain
        device.part_of_domain = network_device.part_of_domain
        device.device_managed_by = network_device.device_managed_by
        device.device_disabled = network_device.device_disabled

        # General info things
        device.last_used_users = network_device.last_used_users
        device.installed_software = network_device.installed_software
        device.users = network_device.users
        device.security_patches = network_device.security_patches
        device.available_security_patches = network_device.available_security_patches

        if network_device.physical_location:
            device.ad_site_location = network_device.physical_location
            device.ad_site_name = f'{device.ad_site_location}-Network'

        ips = mock_utils.get_all_ips(network_device)
        if ips:
            device.add_nic(None, ips)

        yield device

    @staticmethod
    def _parse_user(user: ActiveDirectoryAdapter.MyUserAdapter, network_user: MockNetworkUser):
        org_to_ad_format = ','.join(f'DC={org_part}' for org_part in network_user.domain.split('.'))
        user.username = network_user.username
        user.first_name = network_user.first_name
        user.last_name = network_user.last_name
        user.id = f'CN={user.username.split("@")[0].lower()},CN=Users,{org_to_ad_format}'
        user.mail = network_user.mail
        user.domain = network_user.domain
        user.employee_id = network_user.employee_id
        user.user_telephone_number = network_user.user_telephone_number
        user.display_name = network_user.display_name
        user.first_name = network_user.first_name
        user.last_name = network_user.last_name
        user.user_city = network_user.user_city
        user.is_local = network_user.is_local
        user.last_password_change = network_user.last_password_change
        user.is_locked = network_user.is_locked
        user.password_not_required = network_user.password_not_required
        user.password_never_expires = network_user.password_never_expires
        user.account_disabled = network_user.account_disabled
        user.is_admin = network_user.is_admin

        # ad stuff
        user.ad_distinguished_name = user.id
        user.ad_display_name = user.first_name + ' ' + user.last_name
        user.ad_uac_password_not_required = network_user.password_not_required
        user.ad_uac_dont_expire_password = network_user.password_never_expires

        yield user
