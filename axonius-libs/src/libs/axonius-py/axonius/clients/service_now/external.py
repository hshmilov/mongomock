import logging
from datetime import datetime
from typing import Dict

from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.exception import RESTException
from axonius.clients.service_now.akana import ServiceNowAkanaConnection
from axonius.clients.service_now.base import ServiceNowConnectionMixin
from axonius.clients.service_now.connection import ServiceNowConnection
from axonius.clients.service_now.parse import inject_subtables_fields_to_device, inject_subtables_fields_to_user, \
    InjectedRawFields
from axonius.clients.service_now.sql import ServiceNowMSSQLConnection
from axonius.clients.service_now.service import sql_consts

logger = logging.getLogger(f'axonius.{__name__}')


def generic_service_now_query_devices_by_client(client_data):
    """
    External process version of get_device_list
    """
    config, get_connection_func, install_status_dict, operational_status_dict, get_entities_kwargs, \
        verification_install_status_dict, verification_operational_status_dict = client_data
    connection: ServiceNowConnectionMixin = get_connection_func(config)
    with connection:

        logger.info(f'Retrieving device subtables (this can take a couple of minutes)')
        time_before_subtables = datetime.now()
        device_subtables: Dict[str, dict] = connection.get_device_subtables(**get_entities_kwargs)
        subtables_time = datetime.now() - time_before_subtables
        logger.info(f'Done retrieving subtables. took {subtables_time.seconds}')

        for device_type, device_raw in connection.get_device_list(**get_entities_kwargs):
            device_raw[InjectedRawFields.ax_device_type.value] = device_type
            inject_subtables_fields_to_device(device_subtables, device_raw,
                                              use_dotwalking=get_entities_kwargs.get('use_dotwalking'))
            yield device_raw, install_status_dict, operational_status_dict, \
                verification_install_status_dict, verification_operational_status_dict


def generic_service_now_query_users_by_client(client_data):
    config, get_connection_func, _, _, get_entities_kwargs, *_ = client_data
    connection: ServiceNowConnectionMixin = get_connection_func(config)
    with connection:

        logger.info(f'Retrieving user subtables (this can take a couple of minutes)')
        time_before_subtables = datetime.now()
        user_subtables: Dict[str, dict] = connection.get_user_subtables(**get_entities_kwargs)
        subtables_time = datetime.now() - time_before_subtables
        logger.info(f'Done retrieving subtables. took {subtables_time.seconds}')

        for user_raw in connection.get_user_list(**get_entities_kwargs):
            inject_subtables_fields_to_user(user_subtables, user_raw,
                                            use_dotwalking=get_entities_kwargs.get('use_dotwalking'))
            yield user_raw


def service_now_get_connection(client_config):
    try:
        https_proxy = client_config.get('https_proxy')
        if https_proxy and https_proxy.startswith('http://'):
            https_proxy = 'https://' + https_proxy[len('http://'):]
        connection = ServiceNowConnection(
            domain=client_config['domain'], verify_ssl=client_config['verify_ssl'],
            username=client_config['username'],
            password=client_config['password'], https_proxy=https_proxy)
        with connection:
            pass  # check that the connection credentials are valid
        return connection
    except RESTException as e:
        message = 'Error connecting to client with domain {0}, reason: {1}'.format(
            client_config['domain'], str(e))
        logger.warning(message, exc_info=True)
        raise ClientConnectionException(message)


def service_now_akana_get_connection(client_config):
    try:
        connection = ServiceNowAkanaConnection(domain=client_config.get('domain'),
                                               token_endpoint=client_config.get('token_endpoint'),
                                               # Note - if url_base_prefix does not exist in the client_config,
                                               #    we"ll use ServiceNowAkanaConnection's default
                                               url_base_prefix=client_config.get('url_base_prefix'),
                                               verify_ssl=client_config.get('verify_ssl'),
                                               https_proxy=client_config.get('https_proxy'),
                                               proxy_username=client_config.get('proxy_username'),
                                               proxy_password=client_config.get('proxy_password'),
                                               username=client_config.get('username'),
                                               password=client_config.get('password'))
        with connection:
            pass  # check that the connection credentials are valid
        return connection
    except RESTException as e:
        message = 'Error connecting to client with domain {0}, reason: {1}'.format(
            client_config['domain'], str(e))
        logger.warning(message, exc_info=True)
        raise ClientConnectionException(message)


def service_now_sql_get_connection(
        client_config,
        devices_fetched_at_a_time: int=sql_consts.DEFAULT_DEVICES_FETECHED_AT_A_TIME):

    try:
        connection = ServiceNowMSSQLConnection(
            database=client_config.get(sql_consts.SERVICE_NOW_SQL_DATABASE,
                                       sql_consts.DEFAULT_SERVICE_NOW_SQL_DATABASE),
            server=client_config[sql_consts.SERVICE_NOW_SQL_HOST],
            port=client_config.get(sql_consts.SERVICE_NOW_SQL_PORT,
                                   sql_consts.DEFAULT_SERVICE_NOW_SQL_PORT),
            devices_paging=devices_fetched_at_a_time)
        connection.set_credentials(username=client_config[sql_consts.USER],
                                   password=client_config[sql_consts.PASSWORD])
        with connection:
            pass  # check that the connection credentials are valid
        return connection
    except Exception as e:
        db = client_config.get(sql_consts.SERVICE_NOW_SQL_DATABASE,
                               sql_consts.DEFAULT_SERVICE_NOW_SQL_DATABASE)
        message = f'Error connecting to client host: {client_config[sql_consts.SERVICE_NOW_SQL_HOST]}  ' \
                  f'database: {db}. {str(e)}'
        logger.exception(message)
        raise ClientConnectionException(message)
