import copy
import logging
import time

import botocore.exceptions
from boto3.resources.base import ServiceResource

from axonius.types.enforcement_classes import EntitiesResult
from reports.action_types.base.aws_utils import AWSActionUtils, EC2_ACTION_REQUIRED_ENTITIES, \
    EC2InstanceGroup, EC2ActionResult, EC2ActionCallableReturnType
from reports.action_types.action_type_base import ActionTypeBase, add_node_selection

logger = logging.getLogger(f'axonius.{__name__}')

AWS_ACCESS_KEY_ID = 'aws_access_key_id'
REGION_NAME = 'region_name'
AWS_SECRET_ACCESS_KEY = 'aws_secret_access_key'
AWS_SESSION_TOKEN = 'aws_session_token'
PROXY = 'proxy'
TAG_KEY = 'tag_key'
ACTION_RETRIAL_COUNT = 5


class AwsEc2DeleteTagsAction(ActionTypeBase):
    """
    AWS EC2 Remove Tags from Instances
    Requires "ec2:DeleteTags" IAM policy permission sets.
    For more details see: https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_DeleteTags.html
    """
    @staticmethod
    def config_schema() -> dict:
        schema = copy.deepcopy(AWSActionUtils.config_schema())
        schema['items'].extend([
            {
                'name': TAG_KEY,
                'title': 'Tag keys',
                'type': 'string',
                'description': 'Multiple keys may be specified by using ";" as a separator, e.g. a;b.'
                               ' Each key must not begin with "aws:" (reserved).',
            }])
        schema['required'].append(TAG_KEY)
        return add_node_selection(schema)

    @staticmethod
    def default_config() -> dict:
        return {
            **AWSActionUtils.default_config(),
            TAG_KEY: None,
        }

    @staticmethod
    def delete_tags(
            ec2_resource: ServiceResource,
            instance_group: EC2InstanceGroup,
            client_config: dict) -> EC2ActionCallableReturnType:
        """
        Runs "delete_tags" on the instances within the given group,
            Yields EC2ActionResult results during run.
        :param ec2_resource: EC2 client authorized to "ec2:delete_tags" on instance
        :param instance_group: EC2 instance descriptor
        :param client_config: Config dict with tag_keys
        """
        tag_keys = [tag_key for tag_key in map(str.strip, client_config[TAG_KEY].split(';'))
                    if tag_key]
        if any(tag_key.startswith('aws:') for tag_key in tag_keys):
            return 'Tag key may not start with "aws:".'

        instance_descriptors = instance_group.instance_list
        instances_by_ids = {instance.id: instance for instance in instance_descriptors}
        instance_ids = list(instances_by_ids.keys())
        tags = [{'Key': tag_key} for tag_key in tag_keys]
        logger.info(f'tags to be deleted: {tags}, from machine ids {instance_ids}')
        if not instances_by_ids:
            logger.warning(f'No instance_ids given, exiting.')
            return 'No instances found'

        for ec2_instance in ec2_resource.instances.filter(InstanceIds=instance_ids):

            # Note: this pops the value from the dict such that only machines not found be reported at the end.
            instance_descriptor = instances_by_ids.pop(ec2_instance.id, None)
            if not instance_descriptor:
                logger.error(f'Unable to locate matching instance for {instance_descriptor}')
                continue

            error = None
            for i in range(ACTION_RETRIAL_COUNT):
                try:
                    # pylint: disable=line-too-long
                    # see: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Instance.delete_tags
                    _ = ec2_instance.delete_tags(Tags=tags)
                    logger.info(f'Deleted tag {tags} successfully on attempt {i} from instance: {instance_descriptor}')
                except botocore.exceptions.ClientError as e:
                    if '(RequestLimitExceeded)' in str(e):
                        logger.info(f'Failed to delete tag {tags} on attempt {i} from instance: {instance_descriptor}')
                        if i == (ACTION_RETRIAL_COUNT - 1):
                            logger.error(f'No more attempts left (of {ACTION_RETRIAL_COUNT})'
                                         f' to delete tag {tags} from instance: {instance_descriptor}')
                            break
                        time.sleep(1)
                        continue
                except Exception as e:
                    logger.exception(f'Failed to delete {tags} on attempt {i} from {instance_descriptor}')
                    error = f'AWS Error: {str(e)}'
                yield EC2ActionResult([instance_descriptor], error)
                break

        logger.info(f'Done AWS EC2 delete_tags')

        # yield the rest as "not reported"
        logger.warning(f'The following instances were not reported back: {list(instances_by_ids.keys())}')
        return 'Not reported back by AWS'

    def _run(self) -> EntitiesResult:
        current_result = self._get_entities_from_view({entity: 1 for entity in EC2_ACTION_REQUIRED_ENTITIES})
        yield from AWSActionUtils.perform_grouped_ec2_cfg_action(
            current_result, self._config, self.delete_tags, support_container_ec2_host=True)
