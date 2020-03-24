import copy
import logging

from boto3.resources.base import ServiceResource

from axonius.types.enforcement_classes import EntitiesResult
from reports.action_types.base.aws_utils import AWSActionUtils, EC2_ACTION_REQUIRED_ENTITIES, \
    EC2InstanceGroup, EC2ActionResult, EC2ActionCallableReturnType
from reports.action_types.action_type_base import ActionTypeBase

logger = logging.getLogger(f'axonius.{__name__}')

AWS_ACCESS_KEY_ID = 'aws_access_key_id'
REGION_NAME = 'region_name'
AWS_SECRET_ACCESS_KEY = 'aws_secret_access_key'
AWS_SESSION_TOKEN = 'aws_session_token'
PROXY = 'proxy'
TAG_KEY = 'tag_key'
TAG_VALUE = 'tag_value'


class AwsEc2AddTagsAction(ActionTypeBase):
    """
    AWS EC2 Add Tags to Instances
    Requires "tag:TagResources" and "tag:GetResources" IAM policy permission sets.
    For more details see  https://docs.aws.amazon.com/resourcegroupstagging/latest/APIReference/Welcome.html
    And also  https://docs.aws.amazon.com/resourcegroupstagging/latest/APIReference/API_TagResources.html
    """
    @staticmethod
    def config_schema() -> dict:
        schema = copy.deepcopy(AWSActionUtils.config_schema())
        schema['items'].extend([
            {
                'name': TAG_KEY,
                'title': 'Tag key',
                'type': 'string',
                'description': 'Tag key must not begin with "aws:" (reserved).',
                'default': 'Axonius'
            },
            {
                'name': TAG_VALUE,
                'title': 'Tag value',
                'type': 'string',
                'description': 'Value may be empty.'
            }])
        schema['required'].append(TAG_KEY)
        return schema

    @staticmethod
    def default_config() -> dict:
        return {
            **AWSActionUtils.default_config(),
            TAG_KEY: 'Axonius',
            TAG_VALUE: None,
        }

    @staticmethod
    def add_tags(
            ec2_resource: ServiceResource,
            instance_group: EC2InstanceGroup,
            client_config: dict) -> EC2ActionCallableReturnType:
        """
        Runs "create_tags" on the instances within the given group,
            Yields EC2ActionResult results during run.
        :param ec2_resource: EC2 client authorized to "ec2:create_tags" on instance
        :param instance_group: EC2 instance descriptor
        :param client_config: Config dict with tag_key and (optional) tag_value
        """
        tag_key = client_config.get(TAG_KEY, 'axonius')
        if tag_key.startswith('aws:'):
            raise ValueError('Tag key may not start with "aws:".')
        tag_value = client_config.get(TAG_VALUE, None)
        tags = [{'Key': tag_key, 'Value': tag_value or ''}]

        valid_instance_collection = ec2_resource.instances
        valid_instance_obj_list = instance_group.instance_list
        logger.debug(f'Adding tags to instances {valid_instance_obj_list}')
        _ = valid_instance_collection.create_tags(Tags=tags)
        logger.debug(f'Added tags to instances successfully: {valid_instance_obj_list}')
        yield EC2ActionResult(valid_instance_obj_list, None)

    def _run(self) -> EntitiesResult:
        current_result = self._get_entities_from_view({entity: 1 for entity in EC2_ACTION_REQUIRED_ENTITIES})
        yield from AWSActionUtils.perform_grouped_ec2_cfg_action(
            current_result, self._config, self.add_tags)
