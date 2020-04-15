import copy
import logging

from boto3.resources.base import ServiceResource

from axonius.types.enforcement_classes import EntitiesResult
from reports.action_types.base.aws_utils import AWSActionUtils, EC2_ACTION_REQUIRED_ENTITIES, \
    EC2InstanceGroup, EC2ActionResult, EC2ActionCallableReturnType
from reports.action_types.action_type_base import ActionTypeBase, add_node_selection

logger = logging.getLogger(f'axonius.{__name__}')


class AwsEc2StopInstanceAction(ActionTypeBase):
    """
    AWS EC2 Stop Instance
    Requires "ec2:StopInstances" IAM policy permission.
    """
    default_config = AWSActionUtils.default_config

    @staticmethod
    def config_schema() -> dict:
        schema = copy.deepcopy(AWSActionUtils.config_schema())
        return add_node_selection(schema)

    @staticmethod
    def stop_ec2_instance_group(ec2_resource: ServiceResource, instance_group: EC2InstanceGroup) \
            -> EC2ActionCallableReturnType:
        """
        Runs "StopInstances" on the instances within the given group,
            Yields EC2ActionResult results during run
        :param ec2_client: EC2 client authorized to "ec2:StopInstances" on instance
        :param instance: EC2 instance descriptor
        """

        # pylint: disable=W0212
        filtered_result = (yield from AWSActionUtils._reject_invalid_state_instances(
            ec2_resource, instance_group.instance_list, ['running']))
        if not filtered_result:
            return
        valid_instance_collection, valid_instance_obj_list = filtered_result
        logger.debug(f'Stopping instances {valid_instance_obj_list}')
        _ = valid_instance_collection.stop()
        logger.debug(f'Stopped instances successfully: {valid_instance_obj_list}')
        yield EC2ActionResult(valid_instance_obj_list, None)

    def _run(self) -> EntitiesResult:
        current_result = self._get_entities_from_view({entity: 1 for entity in EC2_ACTION_REQUIRED_ENTITIES})
        yield from AWSActionUtils.perform_grouped_ec2_action(
            current_result, self._config, self.stop_ec2_instance_group)
