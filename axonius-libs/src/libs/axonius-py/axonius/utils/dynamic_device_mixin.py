import logging
import re

from typing import List, Dict, Callable, Tuple, Any, Optional

from axonius.consts.csv_consts import get_csv_field_names
from axonius.devices.device_adapter import DeviceAdapter
from axonius.smart_json_class import SmartJsonClass
from axonius.users.user_adapter import UserAdapter
from axonius.utils.datetime import parse_date
from axonius.utils.dynamic_fields import put_dynamic_field
from axonius.utils.parsing import normalize_var_name

logger = logging.getLogger(f'axonius.{__name__}')


class DynamicParsingCannotProceedError(Exception):
    """
    An Exception thrown if dynamic device/user is lacking required information for the device
    This is the only exception that is reraised from `_fill_field_safely`
    """

# pylint: disable=no-self-use,missing-kwoa,logging-format-interpolation


class DynamicDeviceMixin:
    """
        This mixin implements a generic parsing and filling of raw_dict values into dynamic fields.
        Use it by:
         - (required) Retrieve device object by calling the `fill_dynamic_device`/`fill_dynamic_user` method.
                may throw DynamicParsingCannotProceedError
         - (optionally) adjust `DYNAMIC_FIELD_TITLE_PREFIX`
         - (optionally) override `get_dynamic_field_attributes` with your respective name altering algorithm
        Add Fields to parse:
         - (required) add their normalized key and possible field names into csv_consts.IDENTIFIERS dict
         - (required) add an entry into the filler_to_normalized_fields part of
                      `fill_dynamic_device`/`fill_dynamic_user`
        Method Types:
        - _parse_A methods are responsible to return raw value of normalized field A from device_raw
        - _fill_A methods are responsible to take the raw A and fill it into device.A (logically).
        These methods may raise exceptions which would be safely suppressed and logged except for
            `DynamicDeviceParsingCannotProceedError` which would be reraised to halt device parsing.
        Fill free to override any sub-methods for your specific needs.
        If you override is a generic enhancement, consider performing it in this mixin.
        Warning: Do not call _parse methods from one such to the other to prevent loop.
            There is one exception - _parse_id may call the other _parse methods.
        """

    # This prefix is used for dynamic field names if there's already an existing field in the device with that name.
    #  It may be overriden.
    DYNAMIC_FIELD_TITLE_PREFIX = 'Dynamic'

    def get_dynamic_field_attributes(self, device, column_name) -> Tuple[str, str]:
        """
        normalized column name
        :param column_name:
        """
        field_name = f'{self.DYNAMIC_FIELD_TITLE_PREFIX.lower()}_{normalize_var_name(column_name)}'
        field_title = f'{self.DYNAMIC_FIELD_TITLE_PREFIX} {column_name.title()}'
        return field_name, field_title

    def fill_dynamic_device(self, device: DeviceAdapter, device_raw: dict):
        # Normalized fields are the keys of csv_consts.IDENTIFIERS
        filler_to_normalized_fields = {
            self._fill_id: ['id', 'hostname', 'mac', 'serial'],
            self._fill_name: ['name'],
            self._fill_hostname: ['hostname'],
            self._fill_nics: ['networkinterfaces', 'ip', 'mac'],
            self._fill_model: ['model'],
            self._fill_serial: ['serial'],
            self._fill_os: ['os', 'kernel'],
            self._fill_manufacturer: ['manufacturer'],
            self._fill_total_physical_memory_gb: ['total_physical_memory_gb'],
            self._fill_cpu: ['cpu_speed'],
            self._fill_last_seen: ['last_seen'],
            self._fill_email: ['mail'],
            self._fill_domain: ['domain', 'hostname'],
            self._fill_username: ['username'],
            self._fill_installed_software: ['installed_sw_name', 'installed_sw_version',
                                            'installed_sw_vendor', 'packages'],

        }  # type: Dict[Callable, List[str]]

        self._fill_dynamic_obj(device=device, device_raw=device_raw,
                               fill_callable_to_norm_fields=filler_to_normalized_fields)

    def fill_dynamic_user(self, user: UserAdapter, user_raw: dict):
        # Normalized fields are the keys of csv_consts.IDENTIFIERS
        filler_to_normalized_fields = {
            self._fill_user_id: ['id', 'username', 'name'],
            self._fill_domain: ['domain'],
            self._fill_first_name: ['first_name'],
            self._fill_last_name: ['last_name'],
            self._fill_mail: ['mail'],
            self._fill_display_name: ['name'],
            self._fill_username: ['username'],
        }  # type: Dict[Callable, List[str]]

        self._fill_dynamic_obj(device=user, device_raw=user_raw,
                               fill_callable_to_norm_fields=filler_to_normalized_fields)

    def _fill_dynamic_obj(self, device: SmartJsonClass, device_raw: dict,
                          fill_callable_to_norm_fields: Dict[Callable, List[str]]):
        normalized_field_to_csv_columns = get_csv_field_names(device_raw.keys())  # type: Dict[str, List[str]]

        # Note: all_values maps between normalized field names and the all the matching column's value
        all_values = {field_name: [value for value in map(device_raw.get, csv_columns) if value]
                      for field_name, csv_columns
                      in normalized_field_to_csv_columns.items()}  # type: Dict[str, List[Any]]

        # Note: gen_values is the same but only holds the first value of each field (or None)
        gen_values = {field_name: next(iter(values), None)
                      for field_name, values in all_values.items()}  # type: Dict[str, Optional[Any]]

        # prepare kwargs for filler methods call -
        #   each method may choose which kwargs it wants to use
        kwargs = {
            'device': device,
            'device_raw': device_raw,
            'gen_values': gen_values,
            'all_values': all_values,
        }

        # Handle generic fields
        for filler_method, fields in fill_callable_to_norm_fields.items():
            # curr_values is a filtered version of all_values
            #   to contain only fields relevant to the current field group
            kwargs['curr_values'] = {field_name: values for field_name, values in all_values.items()
                                     if field_name in fields}
            self._fill_field_safely(filler_method=filler_method, **kwargs)

        # And now the dynamic fields....
        try:
            self._fill_dynamic_fields(smart_json_obj=device, **kwargs)
        except Exception as e:
            message = f'Failed to parse dynamic fields for {device_raw}, error {e}'
            logger.warning(message)
            logger.debug(message, exc_info=True)

    def _fill_field_safely(self, *, filler_method: Callable, **kwargs):
        try:
            filler_method(**kwargs)
        except DynamicParsingCannotProceedError:
            logger.warning(f'Parsing cannot proceed for values {kwargs["curr_values"]}')
            raise
        except Exception:
            logger.exception(f'Failed to fill fields {kwargs["curr_values"]}')

    def _fill_dynamic_fields(self, smart_json_obj, *, device_raw, **_):
        for key, val in device_raw.items():
            try:
                if not key or not val:
                    logger.debug(f'Bad item. Key "{key}" ; Value "{val}"')
                    continue
                field_name, field_title = self.get_dynamic_field_attributes(smart_json_obj, key)
                put_dynamic_field(smart_json_obj, field_name, val, field_title)
            except Exception as e:
                logger.warning(f'Failed to add {key}:{val} to entity {smart_json_obj.id}: '
                               f'Got {str(e)}')
                continue

    def _parse_id(self, *, gen_values, **_):
        return gen_values.get('id')

    def _fill_id(self, device: DeviceAdapter, **kwargs):

        # Figure out macs first as a backup id, take the first one encountered
        mac = next((_mac.strip() for _mac in self._parse_mac_address(**kwargs) or [] if _mac.strip()), None)

        # Get an ID
        serial = self._parse_serial(**kwargs)
        hostname = self._parse_hostname(**kwargs)
        if hostname and hostname.lower() == 'unknown':
            hostname = None

        device_id = self._parse_id(**kwargs)
        device_id = '_'.join(str(field) for field in [device_id, serial, mac, hostname] if field)
        if not device_id:
            raise DynamicParsingCannotProceedError('Bad device with no ID')
        device.id = device_id

    def _fill_user_id(self, device: UserAdapter, **kwargs):
        username = self._parse_username(**kwargs)
        name = self._parse_name(**kwargs)

        user_id = self._parse_id(**kwargs)
        user_id = '_'.join(str(field) for field in [user_id, username, name] if field)
        if not user_id:
            raise DynamicParsingCannotProceedError('Bad device with no ID')
        device.id = user_id

    def _parse_name(self, *, gen_values, **_):
        return gen_values.get('name')

    def _fill_name(self, device: DeviceAdapter, **kwargs):
        device.name = self._parse_name(**kwargs)

    def _fill_display_name(self, device: DeviceAdapter, **kwargs):
        device.display_name = self._parse_name(**kwargs)

    def _parse_hostname(self, *, gen_values, **_):
        hostname = gen_values.get('hostname')
        if not isinstance(hostname, str):
            return None
        # if hostname includes '\',
        #   we assume it has domain component which will be taken care later
        return hostname.rsplit('\\', 1)[-1]

    def _fill_hostname(self, device: DeviceAdapter, **kwargs):
        device.hostname = self._parse_hostname(**kwargs)

    def _parse_mac_addresses(self, *, curr_values, **_):
        return [self._parse_mac_address(gen_values={'mac_address': value})
                for value in curr_values.get('mac_address') or []]

    def _parse_mac_address(self, *, gen_values, **_):

        macs = gen_values.get('mac_address')
        if isinstance(macs, str):
            macs = macs.split(',')
            # fallthrough

        if not isinstance(macs, list):
            return None

        return macs

    def _parse_ips(self, *, curr_values, **_):
        return [self._parse_mac_address(gen_values={'ip': value})
                for value in curr_values.get('ip') or []]

    def _parse_ip(self, *, gen_values, **_):

        ips = gen_values.get('ip') or []
        if not ips:
            return []

        if isinstance(ips, str):
            if gen_values.get('ip') == 'unknown':
                return []
            ips = ips.split(',')
            # fallthrough

        if not isinstance(ips, list):
            logger.warning(f'Unknown ips found: {ips}')
            return []

        ips = [ip.strip() for ip in ips if ip.strip()]
        return ips

    def _parse_nics(self, curr_values, **_):
        # pylint: disable=anomalous-backslash-in-string
        try:
            nics_raw = curr_values.get('networkinterfaces')
            if not isinstance(nics_raw, str):
                nics_raw = ''
            macs_nics = re.findall('ether ([^\s]+)', nics_raw)
            macs_nics.extend(re.findall('HWaddr ([^\s]+)', nics_raw))
            ips_nics = re.findall('inet ([^\s]+)', nics_raw)
            ips_nics = [x.strip('addr:') for x in ips_nics]
            return ips_nics, macs_nics
        except Exception:
            logger.exception(f'Problem with nics')

    def _fill_nics(self, device: DeviceAdapter, **kwargs):

        macs = self._parse_mac_addresses(**kwargs)
        ips = self._parse_ips(**kwargs)
        device.add_ips_and_macs(macs=macs, ips=ips)

        macs_nics, ips_nics = self._parse_nics(**kwargs)
        device.add_ips_and_macs(macs=macs_nics, ips=ips_nics)

    def _parse_model(self, *, gen_values, **_):
        return gen_values.get('model')

    def _fill_model(self, device: DeviceAdapter, **kwargs):
        device.device_model = self._parse_model(**kwargs)

    def _parse_serial(self, *, gen_values, **_):
        return gen_values.get('serial')

    def _fill_serial(self, device: DeviceAdapter, **kwargs):
        device.device_serial = self._parse_serial(**kwargs)

    def _parse_kernel(self, *, gen_values, **_):
        return gen_values.get('kernel')

    def _parse_os(self, *, curr_values, **_):
        # OS is a special case, instead of getting the first found key we take all
        # of them and combine them!
        os_components = curr_values.get('os')
        if not os_components:
            return None
        return '_'.join(os_components)

    def _fill_os(self, device: DeviceAdapter, **kwargs):
        os = self._parse_os(**kwargs)
        if not os:
            return
        device.figure_os(os)
        device_kernel = self._parse_kernel(**kwargs)
        if device_kernel:
            try:
                device.os.kernel_version = device_kernel
            except Exception:
                return

    def _parse_manufacturer(self, *, gen_values, **_):
        return gen_values.get('manufacturer')

    def _fill_manufacturer(self, device: DeviceAdapter, **kwargs):
        device.device_manufacturer = self._parse_manufacturer(**kwargs)

    def _parse_total_physical_memory_gb(self, *, gen_values, **_):
        physical_memory_gb = gen_values.get('total_physical_memory_gb')
        if isinstance(physical_memory_gb, (str, int)):
            try:
                physical_memory_gb = float(physical_memory_gb)
            except Exception:
                pass
            # fallthrough
        if not isinstance(physical_memory_gb, float):
            return None
        return physical_memory_gb

    def _fill_total_physical_memory_gb(self, device: DeviceAdapter, **kwargs):
        device.total_physical_memory = self._parse_total_physical_memory_gb(**kwargs)

    def _parse_cpu_speed(self, *, gen_values, **_):
        cpu_speed = gen_values.get('cpu_speed')
        if not cpu_speed:
            return None
        if isinstance(cpu_speed, (str, int)):
            try:
                cpu_speed = float(cpu_speed)
            except Exception:
                return None
            # fallthrough
        if not isinstance(cpu_speed, float):
            return None
        return cpu_speed / (1024 ** 3.0)

    def _fill_cpu(self, device: DeviceAdapter, **kwargs):

        cpu_speed = self._parse_cpu_speed(**kwargs)
        if cpu_speed:
            device.add_cpu(ghz=cpu_speed)

    def _parse_last_seen(self, *, curr_values, **_):
        last_seen_vals = [dt for dt in map(parse_date, curr_values.get('last_seen') or []) if dt]
        if not last_seen_vals:
            return None
        return max(last_seen_vals)

    def _fill_last_seen(self, device: DeviceAdapter, **kwargs):
        device.last_seen = self._parse_last_seen(**kwargs)

    def _parse_mail(self, *, gen_values, **_):
        return gen_values.get('mail')

    def _fill_email(self, device: DeviceAdapter, **kwargs):
        device.email = self._parse_mail(**kwargs)

    def _fill_mail(self, device: DeviceAdapter, **kwargs):
        device.mail = self._parse_mail(**kwargs)

    def _parse_domain(self, *, gen_values, **_):

        domain = gen_values.get('domain')

        if not isinstance(domain, str):
            # fallback to domain from hostname
            hostname = gen_values.get('hostname')
            if not isinstance(hostname, str):
                return None
            domain = hostname.split('\\', 1)[0]
        return domain

    def _fill_domain(self, device: DeviceAdapter, **kwargs):
        device.domain = self._parse_domain(**kwargs)

    def _parse_username(self, *, gen_values, **_):
        return gen_values.get('username')

    def _fill_username(self, device: SmartJsonClass, **kwargs):
        username = self._parse_username(**kwargs)
        if isinstance(username, str):
            if isinstance(device, DeviceAdapter):
                device.last_used_users = [username]
            elif isinstance(device, UserAdapter):
                device.username = username

    def _parse_installed_sw_name(self, *, gen_values, **_):
        return gen_values.get('installed_sw_name')

    def _parse_installed_sw_version(self, *, gen_values, **_):
        return gen_values.get('installed_sw_version')

    def _parse_installed_sw_vendor(self, *, gen_values, **_):
        return gen_values.get('installed_sw_vendor')

    def _parse_packages(self, *, gen_values, **_):
        package_names = []
        try:
            packages = gen_values.get('packages')
            if packages and isinstance(packages, str):
                packages = packages.split(' ')
            if packages and isinstance(packages, list):
                for package in packages:
                    if (not isinstance(package, str)) or (len(package) >= 100):
                        continue
                    package_names.append(package)
        except Exception:
            logger.exception(f'Problem with packages')
        return package_names

    def _fill_installed_software(self, device: DeviceAdapter, **kwargs):

        device.add_installed_software(
            name=self._parse_installed_sw_name(**kwargs),
            version=self._parse_installed_sw_version(**kwargs),
            vendor=self._parse_installed_sw_vendor(**kwargs),
        )

        for package in self._parse_packages(**kwargs) or []:
            device.add_installed_software(name=package)

    def _parse_cve_id(self, *, gen_values, **_):
        cve_ids = gen_values.get('cve_id')
        if isinstance(cve_ids, str):
            cve_ids = cve_ids.split(',')
            # fallthrough
        if not isinstance(cve_ids, list):
            return []
        return cve_ids

    def _fill_cve_id(self, device: DeviceAdapter, **kwargs):
        for cve_id in self._parse_cve_id(**kwargs) or []:
            device.add_vulnerable_software(cve_id=cve_id)

    def _parse_first_name(self, *, gen_values, **_):
        return gen_values.get('first_name')

    def _fill_first_name(self, device: SmartJsonClass, **kwargs):
        device.first_name = self._parse_first_name(**kwargs)

    def _parse_last_name(self, *, gen_values, **_):
        return gen_values.get('last_name')

    def _fill_last_name(self, device: SmartJsonClass, **kwargs):
        device.last_name = self._parse_last_name(**kwargs)
