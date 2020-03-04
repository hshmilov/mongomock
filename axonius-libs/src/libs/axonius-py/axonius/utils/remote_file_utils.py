
import logging
from typing import Tuple
import urllib
from urllib.parse import urlparse

import chardet
import requests

from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.aws.utils import get_s3_object
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.consts import get_default_timeout
from axonius.consts.remote_file_consts import (AWS_ENDPOINT_FOR_REACHABILITY_TEST,
                                               RESOURCE_PATH_DESCRIPTION)
from axonius.plugin_base import PluginBase
from axonius.utils.json import from_json
from axonius.utils.remote_file_smb_handler import get_smb_handler

logger = logging.getLogger(f'axonius.{__name__}')


def load_from_s3(client_config) -> bytes:
    s3_bucket = client_config.get('s3_bucket')
    s3_obj_loc = client_config.get('s3_object_location')
    if not (s3_bucket and s3_obj_loc):
        message = f'Error - Please specify both Amazon S3 Bucket and ' \
                  f'Amazon S3 Object Location'
        raise ClientConnectionException(message)

    s3_access_key_id = client_config.get('s3_access_key_id')
    s3_secret_access_key = client_config.get('s3_secret_access_key')

    # check logical_xor(key_id, secret_key)
    # if bool(a) != bool(b) then either only one of a,b is True and the other is False
    # If this condition is true, then exactly one of the two values was specified.
    # Legal conditions are that either none or both are specified.
    if bool(s3_access_key_id) != bool(s3_secret_access_key):
        message = f'Error - Please specify both access key id and secret access key, ' \
                  f'or leave both blank to use the attached IAM role'
        raise ClientConnectionException(message)

    https_proxy = client_config.get('https_proxy')

    # Now we can proceed to try an get an object
    try:
        return get_s3_object(
            bucket_name=s3_bucket,
            object_location=s3_obj_loc,
            access_key_id=s3_access_key_id,
            secret_access_key=s3_secret_access_key,
            https_proxy=https_proxy
        )
    except Exception as e:
        if 'SignatureDoesNotMatch' in str(e):
            message = f'Amazon S3 Bucket - Invalid Credentials. Response is: {str(e)}'
            raise ClientConnectionException(message)
        raise


def load_from_url(client_config) -> bytes:
    url = client_config.get('resource_path')
    headers = None
    raw_additional_headers = client_config.get('request_headers')
    if raw_additional_headers:
        try:
            headers = from_json(raw_additional_headers)
        except Exception as e:
            message = f'Failed to parse additional headers from {raw_additional_headers}: {str(e)}'
            logger.exception(message)
            raise ClientConnectionException(message)
    username = client_config.get('username')
    password = client_config.get('password')
    # support basic auth with only username or only password
    # and also username+password
    # example: username is an api key for basic auth
    # see for example https://github.com/postmanlabs/httpbin/issues/356
    auth = (username, password) if (username or password) else None
    proxies = {
        'http': client_config.get('http_proxy') or None,
        'https': client_config.get('https_proxy') or None
    }
    try:
        response = requests.get(url,
                                verify=client_config.get('verify_ssl', False),
                                timeout=get_default_timeout(),
                                headers=headers,
                                auth=auth,
                                proxies=proxies
                                )
        if response.status_code != 200:
            raise ClientConnectionException(
                f'Error - got status code {response.status_code}. Content is {str(response.content)}')
        return response.content
    except Exception as e:
        message = f'Failed to get resource from URL: {str(e)}'
        logger.exception(message)
        raise ClientConnectionException(message)


def load_from_smb(client_config) -> bytes:
    try:
        username = client_config.get('username')
        password = client_config.get('password')
        use_netbios = not client_config.get('suppress_netbios', False)
        if not use_netbios:
            logger.info(f'Using alternate smb handler for {client_config.get("user_id")}')
        handler = get_smb_handler(use_netbios)
        # We don't actually need the double-backslash
        # We just wanted to make sure it was a valid path
        share_path = client_config.get('resource_path')[2:]
        share_path = share_path.replace('\\', '/')
        if username and password:
            share_path = f'{urllib.parse.quote(username)}:' \
                         f'{urllib.parse.quote(password)}@{share_path}'
        elif username:
            # support guest or password-less smb auth
            share_path = f'{urllib.parse.quote(username)}@{share_path}'
        final_path = f'smb://{share_path}'
        opener = urllib.request.build_opener(handler)
        with opener.open(final_path) as file_obj:
            return file_obj.read()
    except Exception as e:
        message = f'Error - Failed to read from SMB Share: {str(e)}'
        logger.exception(message)
        raise ClientConnectionException(message)


def load_local_file(client_config) -> bytes:
    return PluginBase.Instance.grab_local_file(client_config['file_path'])


def load_remote_binary_data(client_config) -> bytes:
    """
    Load binary data from a remote file, using client config.
    :param client_config: Client configuration dictionary.
                          Should match ``remote_file_consts.FILE_CLIENTS_SCHEMA``.
    :return: bytes file_data
    """

    if not client_config.get('user_id'):
        raise ClientConnectionException('File name is required.')

    if client_config.get('resource_path'):
        # May raise AttributeError, this is intentional.
        resource_path = client_config.get('resource_path').lower()
        if resource_path.startswith('http'):
            data_bytes = load_from_url(client_config)
        elif resource_path.startswith('\\\\'):
            data_bytes = load_from_smb(client_config)
        else:
            message = f'Error - Invalid path to resource. Please supply a path according ' \
                      f'to the following guidelines: {RESOURCE_PATH_DESCRIPTION}'
            raise ClientConnectionException(message)
    elif client_config.get('s3_bucket') or client_config.get('s3_object_location'):
        data_bytes = load_from_s3(client_config)
    elif client_config.get('file_path'):
        data_bytes = load_local_file(client_config)
    else:
        message = f'Error - No way to find the resource from config.'
        raise ClientConnectionException(message)

    return data_bytes


def load_remote_data(client_config, default_encoding='utf-8') -> Tuple[str, str]:
    """
    Load data from a remote file, using client config.
    :param client_config: Client configuration dictionary.
                          Should match ``remote_file_consts.FILE_CLIENTS_SCHEMA``.
    :param default_encoding: Default encoding if encoding not configured. Defaults to utf-8.
    :return: tuple(file_name, file_data)
    """

    data_bytes = load_remote_binary_data(client_config)

    if not client_config.get('encoding'):
        encoding = chardet.detect(data_bytes)['encoding']  # detect decoding automatically
        encoding = encoding or default_encoding
    else:
        encoding = client_config.get('encoding')

    return client_config['user_id'], data_bytes.decode(encoding)


def test_file_reachability(client_config):
    """
    Test the ability Load data from a remote file, using client config.
    :param client_config: Client configuration dictionary.
                          Should match ``remote_file_consts.FILE_CLIENTS_SCHEMA``.
    :return: True if file is reachable, false if not.
    """
    if client_config.get('file_path'):
        return True
    if client_config.get('s3_bucket') or client_config.get('s3_object_location'):
        return RESTConnection.test_reachability(AWS_ENDPOINT_FOR_REACHABILITY_TEST)
    if client_config.get('resource_path'):
        # May raise TypeError, this is intentional.
        resource_path = client_config.get('resource_path').lower()
        if resource_path.startswith('http'):
            parsed_url = urlparse(resource_path)
            port = parsed_url.port
            http_proxy = client_config.get('http_proxy')
            https_proxy = client_config.get('https_proxy')
            return RESTConnection.test_reachability(resource_path,
                                                    port=port,
                                                    https_proxy=https_proxy,
                                                    http_proxy=http_proxy)
        if resource_path.startswith('\\\\'):
            share_path = resource_path[2:]
            share_path = 'smb://' + share_path.replace('\\', '/')
            parsed_url = urlparse(share_path)
            test_445 = RESTConnection.test_reachability(parsed_url.hostname, port=445)
            test_137 = RESTConnection.test_reachability(parsed_url.hostname, port=137)
            return test_445 and test_137
        logger.error('Test reachability failed: resource_path invalid')
        return False
    logger.error('Test reachability failed: Invalid configuration.')
    return False
