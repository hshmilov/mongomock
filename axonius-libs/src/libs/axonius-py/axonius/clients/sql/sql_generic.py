import logging

from axonius.fields import Field
from axonius.utils.datetime import parse_date
from axonius.utils.parsing import normalize_var_name
from axonius.utils.sql import SQLTypes
from axonius.adapter_exceptions import GetDevicesError
from axonius.consts.csv_consts import get_csv_field_names

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=too-many-branches, too-many-statements, too-many-locals, too-many-nested-blocks, logging-format-interpolation
def _sql_parse_raw_data(create_adapter_func, devices_raw_data):
    first_time = True
    fields = {}
    for device_raw, client_config, sql_type in devices_raw_data:
        try:
            if first_time:
                fields = get_csv_field_names(device_raw.keys())
                first_time = False
            if not any(id_field in fields for id_field in ['id', 'serial', 'mac_address', 'hostname']):
                logger.error(f'Bad devices fields names {device_raw.keys()}')
                raise GetDevicesError(f'Strong identifier is missing for devices')
            device = create_adapter_func()
            vals = {field_name: device_raw.get(fields[field_name][0]) for field_name in fields}
            macs = (vals.get('mac_address') or '').split(',')
            macs = [mac.strip() for mac in macs if mac.strip()]
            mac_as_id = macs[0] if macs else None

            device_id = str(vals.get('id', '')) or vals.get('serial') or mac_as_id or vals.get('hostname')
            if not device_id:
                logger.error(f'can not get device id for {device_raw}, continuing')
                continue
            device.id = device_id
            device.table = client_config.get('table')
            if sql_type.lower() == SQLTypes.SQLITE.value.lower():
                device.file_name = client_config.get('user_id')
            device.database = client_config.get('database')
            device.server_tag = client_config.get('server_tag')

            device.device_serial = vals.get('serial')
            device.name = vals.get('name')
            device.hostname = vals.get('hostname')
            device.device_model = vals.get('model')
            device.domain = vals.get('domain')
            device.last_seen = parse_date(vals.get('last_seen'))
            device.device_manufacturer = vals.get('manufacturer')
            device.total_physical_memory = vals.get('total_physical_memory_gb')

            # OS is a special case, instead of getting the first found column we take all of them and combine them
            if 'os' in fields:
                try:
                    os_raw = ''
                    for os_column in fields['os']:
                        if device_raw.get(os_column) and isinstance(device_raw.get(os_column), str):
                            os_raw += device_raw.get(os_column) + ' '
                    device.figure_os(os_raw)
                except Exception:
                    logger.error(f'Can not parse os')

            try:
                device.os.kernel_version = vals.get('kernel')
            except Exception:
                # os is probably not set
                device.figure_os('')
                device.os.kernel_version = vals.get('kernel')

            try:
                cpu_speed = vals.get('cpu_speed')
                architecture = vals.get('architecture')
                if cpu_speed or architecture:
                    device.add_cpu(ghz=cpu_speed / (1024 ** 3), architecture=architecture)
            except Exception:
                logger.exception(f'Problem setting cpu')
            try:
                ips = None
                if isinstance(vals.get('ip'), str):
                    ips = (vals.get('ip') or '').split(',')
                    ips = [ip.strip() for ip in ips if ip.strip()]
                device.add_ips_and_macs(macs=macs, ips=ips)
            except Exception:
                logger.exception(f'Problem getting nic and ips for {device_raw}')

            device.set_raw(device_raw)

            for column_name, column_value in device_raw.items():
                try:
                    if sql_type.lower() == SQLTypes.SQLITE.value.lower():
                        normalized_column_name = sql_type.lower() + '_' + normalize_var_name(column_name)
                    else:
                        normalized_column_name = 'mssql_' + '_' + normalize_var_name(column_name)
                    if not device.does_field_exist(normalized_column_name):
                        # Currently we treat all columns as str
                        cn_capitalized = ' '.join([word.capitalize() for word in column_name.split(' ')])
                        device.declare_new_field(normalized_column_name,
                                                 Field(str, f'{sql_type.upper()} {cn_capitalized}'))
                        if sql_type.lower() == SQLTypes.SQLITE.value.lower():
                            device.declare_new_field(normalized_column_name,
                                                     Field(str, f'{sql_type.upper()} {cn_capitalized}'))
                        else:
                            device.declare_new_field(normalized_column_name, Field(str, f'MSSQL {cn_capitalized}'))

                    device[normalized_column_name] = column_value
                except Exception:
                    logger.warning(f'Could not parse column {column_name} with value {column_value}', exc_info=True)

            device.set_raw(device_raw)
            yield device
        except Exception:
            logger.exception(f'Problem with fetching {sql_type} Device for {device_raw}')
