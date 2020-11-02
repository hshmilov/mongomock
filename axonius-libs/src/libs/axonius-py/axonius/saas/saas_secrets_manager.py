# Should be imported from inside the docker and outside the docker
import boto3

from axonius.saas.input_params import get_stack_name, get_params_key_id, get_aws_region


class SaasSecretsManager:
    def __init__(self):
        self._aws_region = get_aws_region()
        self._ssm_client = boto3.client('ssm', region_name=self._aws_region)
        self._stack_name = get_stack_name()
        self._stack_secrets_prefix = f'/stacks/{self._stack_name}'
        self._key_id = get_params_key_id()

    def store_admin_password_reset_link(self, value):
        self._ssm_client.put_parameter(Name=f'{self._stack_secrets_prefix}/admin_password_reset',
                                       Value=value,
                                       Type='SecureString',
                                       KeyId=self._key_id,
                                       Overwrite=True)
