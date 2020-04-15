import copy
import logging

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


class AwsEc2StartInstanceAction(ActionTypeBase):
    """
    AWS EC2 Start Instance
    Requires "ec2:StartInstances" IAM policy permission.
    """
    default_config = AWSActionUtils.default_config

    @staticmethod
    def config_schema() -> dict:
        schema = copy.deepcopy(AWSActionUtils.config_schema())
        return add_node_selection(schema)

    @staticmethod
    def start_ec2_instance_group(ec2_resource: ServiceResource, instance_group: EC2InstanceGroup) \
            -> EC2ActionCallableReturnType:
        """
        Runs "StartInstances" on the instances within the given group,
            Yields EC2ActionResult results during run.
        :param ec2_client: EC2 client authorized to "ec2:StartInstances" on instance
        :param instance: EC2 instance descriptor
        """

        # pylint: disable=W0212
        filtered_result = (yield from AWSActionUtils._reject_invalid_state_instances(
            ec2_resource, instance_group.instance_list, ['stopped']))
        if not filtered_result:
            return
        valid_instance_collection, valid_instance_obj_list = filtered_result
        logger.debug(f'Starting instances {valid_instance_obj_list}')
        _ = valid_instance_collection.start()
        logger.debug(f'Started instances successfully: {valid_instance_obj_list}')
        yield EC2ActionResult(valid_instance_obj_list, None)

    def _run(self) -> EntitiesResult:
        current_result = self._get_entities_from_view({entity: 1 for entity in EC2_ACTION_REQUIRED_ENTITIES})
        yield from AWSActionUtils.perform_grouped_ec2_action(
            current_result, self._config, self.start_ec2_instance_group)
