from typing import Dict

from reports.action_types.action_type_base import ActionTypeBase
from reports.action_types.carbonblack_isolate import CarbonblackIsolateAction
from reports.action_types.carbonblack_unisolate import CarbonblackUnisolateAction
from reports.action_types.create_servicenow_computer import ServiceNowComputerAction
from reports.action_types.run_cmd import RunCmd
from reports.action_types.run_executable import RunExecutable
from reports.action_types.tag_all_entities import TagAllEntitiesAction
from reports.action_types.untag_all_entities import UntagAllEntitiesAction

AllActionTypes: Dict[str, type(ActionTypeBase)] = {
    'create_service_now_computer': ServiceNowComputerAction,
    'tag': TagAllEntitiesAction,
    'carbonblack_isolate': CarbonblackIsolateAction,
    'carbonblack_unisolate': CarbonblackUnisolateAction,
    'untag': UntagAllEntitiesAction,
    'run_executable_windows': RunExecutable,
    'run_command_windows': RunCmd
}
