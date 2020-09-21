import json
import logging

import boto3

from axonius.clients.abstract.abstract_vault_connection import AbstractVaultConnection, VaultException, VaultProvider
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class AWSSecretsManagerException(VaultException):
    def __init__(self, field_name, *args, **kwargs):
        super().__init__(VaultProvider.AWSSecretsManager, field_name, *args, **kwargs)


class AWSSecretsManager(AbstractVaultConnection):

    def __init__(self, *args, access_key_id=None, secret_access_key=None, region=None, **kwargs):
        super().__init__(*args,
                         domain='',
                         headers={'Content-Type': 'application/x-www-form-urlencoded',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._access_key_id = access_key_id
        self._secret_access_key = secret_access_key
        self._region = region

    def _connect(self):
        if not (self._access_key_id and self._secret_access_key and self._region):
            raise RESTException('No access key id, secret access key or region')

    def query_password(self, adapter_field_name, vault_data) -> str:
        try:
            self._session = boto3.Session(aws_access_key_id=self._access_key_id,
                                          aws_secret_access_key=self._secret_access_key)
        except Exception as e:
            raise AWSSecretsManagerException(adapter_field_name,
                                             f'Couldn\'t create session for {self._access_key_id}, Error: {e}')

        try:
            self._client = self._session.client('secretsmanager', region_name=self._region)
        except Exception as e:
            raise AWSSecretsManagerException(adapter_field_name,
                                             f'Couldn\'t create client for {self._access_key_id},'
                                             f' region: {self._region}, Error: {e}')
        try:
            secret = self._client.get_secret_value(SecretId=vault_data.get('name'))
            if not isinstance(secret, dict):
                raise AWSSecretsManagerException(adapter_field_name, f'Couldn\'t find secret for {vault_data}')

            secret_json = json.loads(secret.get('SecretString'))
            if not secret_json.get(vault_data.get('secret_key')):
                raise AWSSecretsManagerException(adapter_field_name, f'Couldn\'t find secret for {vault_data}')
            return secret_json.get(vault_data.get('secret_key'))

        except Exception as e:
            raise AWSSecretsManagerException(adapter_field_name, f'Couldn\'t find secret for {vault_data}, Error: {e}')
