import boto3

from scripts.saas.input_params import get_stack_name, get_params_key_id


class SaasSecretsManager:
    def __init__(self):
        self._ssm_client = boto3.client('ssm', region_name='us-east-1')
        self._stack_name = get_stack_name()
        self._stack_secrets_prefix = f'/stacks/{self._stack_name}'
        self._key_id = get_params_key_id()

    def store_admin_password_reset_link(self, value):
        self._ssm_client.put_parameter(Name=f'{self._stack_secrets_prefix}/admin_password_reset',
                                       Value=value,
                                       Type='SecureString',
                                       KeyId=self._key_id,
                                       Overwrite=True)
