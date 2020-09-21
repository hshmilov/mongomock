import logging
from abc import abstractmethod
from enum import Enum
from axonius.clients.rest.connection import RESTConnection
from axonius.consts.plugin_consts import PASSWORD_MANGER_CYBERARK_VAULT, PASSWORD_MANGER_THYCOTIC_SS_VAULT, \
    PASSWORD_MANGER_AWS_SM_VAULT

logger = logging.getLogger(f'axonius.{__name__}')


class VaultProvider(Enum):
    Thycotic = PASSWORD_MANGER_THYCOTIC_SS_VAULT
    CyberArk = PASSWORD_MANGER_CYBERARK_VAULT
    AWSSecretsManager = PASSWORD_MANGER_AWS_SM_VAULT


class VaultException(Exception):

    def __init__(self, vault_provider: VaultProvider, field_name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._field_name = field_name
        self._vault_provider = vault_provider

    def __repr__(self):
        # This is so the gui will recognize this specific error and to what field it's relevant to.
        return f'{self._vault_provider.value}_error:{self._field_name}:{super(VaultException,self).__repr__()}'

    def __str__(self):
        # This is so the gui will recognize this specific error and to what field it's relevant to.
        return f'{self._vault_provider.value}_error:{self._field_name}:{super(VaultException,self).__str__()}'


class AbstractVaultConnection(RESTConnection):

    def get_device_list(self):
        pass

    def __init__(self,
                 *args,
                 **kwargs):

        super().__init__(*args, **kwargs)

    @abstractmethod
    def query_password(self, adapter_field_name, vault_data) -> str:
        pass
