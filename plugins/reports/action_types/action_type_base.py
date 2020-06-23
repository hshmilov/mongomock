import logging
import copy
import traceback
from abc import ABC, abstractmethod
from typing import Set, List, Iterable

from axonius.consts.core_consts import ACTIVATED_NODE_STATUS
from axonius.consts.plugin_consts import PLUGIN_NAME, NODE_ID
from axonius.entities import EntityType
from axonius.logging.audit_helper import AuditCategory, AuditType, AuditAction
from axonius.plugin_base import PluginBase
from axonius.types.enforcement_classes import Trigger, ActionRunResults, EntitiesResult, EntityResult, TriggeredReason
from axonius.utils.db_querying_helper import iterate_axonius_entities

logger = logging.getLogger(f'axonius.{__name__}')

DEFAULT_INSTANCE = 'Master'
INSTANCE = 'instance'

INSTANCE_ITEM = {
    'name': INSTANCE,
    'title': 'Instance Name',
    'type': 'string',
    'enum': [],
    'source': {
        'key': 'all-instances',
        'options': {
            'allow-custom-option': False
        }
    }
}


# pylint: disable=W0212

def generic_success(internal_axon_ids: Iterable[str], reason: str = 'Success') -> EntitiesResult:
    """
    Returns generic successful result
    :param internal_axon_ids: The IDs the action was successful on
    :param reason: The success reasnn
    :return: A proper return value for _run
    """
    return [EntityResult(x, True, reason) for x in internal_axon_ids]


def generic_fail(internal_axon_ids: Iterable[str], reason: str = 'Failure') -> EntitiesResult:
    """
    See generic_success
    """
    return [EntityResult(x, False, reason) for x in internal_axon_ids]


def _get_list_of_nodes_with_online_adapter(adapter_name: str) -> list:
    # creating a list of adapters with the requested adapter_name from core.
    adapters_list = filter(lambda x: x[PLUGIN_NAME] == adapter_name,
                           PluginBase.Instance.get_available_plugins_from_core_uncached().values())

    # Filtering just the node_id
    active_nodes = [node['node_id'] for node in PluginBase.Instance._get_nodes_table() if node['status']
                    == ACTIVATED_NODE_STATUS]
    nodes_with_adapter = [adapter[NODE_ID] for adapter in adapters_list if adapter[NODE_ID] in active_nodes]
    return nodes_with_adapter


def add_node_selection(config_schema: dict = None) -> dict:
    """
    Adds the appropriate node selection (only nodes with the specific adapter online) dropdown to the action schema
    :param config_schema: The existing schema without the nodes.
    :type config_schema: dict
    :return: A schema dict
    """
    if not config_schema:
        config_schema = {}
    # Copying schema
    schema = copy.deepcopy(config_schema)

    # Setting up default in dropdown
    instance_item = copy.deepcopy(INSTANCE_ITEM)

    # Adding instances to schema
    if 'items' in schema:
        schema['items'].append(instance_item)
    else:
        schema['items'] = [instance_item]

    if 'required' in schema:
        schema['required'].append(INSTANCE)
    else:
        schema['required'] = [INSTANCE]

    if 'type' not in schema:
        schema['type'] = 'array'
    else:
        if schema['type'] != 'array':
            raise Exception('The actions schema type should always be array.')

    return schema


def add_node_default(default_config: dict = None) -> dict:
    """
    Adding the instances node default to the default schema dict.
    :param default_config: The existing schema without the default instance to use
    :type default_config: dict
    :return: The correct schema with the instances default.
    """

    if not default_config:
        default_config = {}
    default_config[INSTANCE] = PluginBase.Instance.node_id
    return default_config


class ActionTypeBase(ABC):
    """
    Base type for an ActionType
    Important: This is only meant to run from the Reports plugin!

    see https://axonius.atlassian.net/wiki/spaces/AX/pages/793051137/New+Actions+Center

    An "Action" is always a part of a recipe.
    In the CTOR below, the 'internal_axon_ids' is the entities that are to be acted upon according to the
    recipe: e.g. only failing devices. The rest is data that general to the alert.
    """

    def __init__(self,
                 action_saved_name: str,
                 config,
                 run_configuration: Trigger,
                 report_data: dict, triggered_set: Set[TriggeredReason],
                 internal_axon_ids: List[str],
                 entity_type: EntityType):
        """
        CTOR
        :param action_saved_name: The name of the saved action as it is in the db
        :param config: Should conform to 'config_schema'
        :param run_configuration: The RunConfiguration that was used for the run of the current recipe
        :param report_data: The report as it is in the DB
        :param triggered_set: Set of reasons why this was triggered, see ReportsService._get_triggered_reports
        :param internal_axon_ids: The list of entities to run on according to the stages in the recipe
        :param entity_type: The entity type used
        """
        super().__init__()
        self._action_saved_name = action_saved_name
        self._config = config
        self._run_configuration = run_configuration
        self._report_data = report_data
        self._triggered_set = triggered_set
        self._internal_axon_ids = internal_axon_ids
        self._entity_type = entity_type
        self._plugin_base = PluginBase.Instance

    @property
    def entity_db(self):
        """
        The entity_db according to entity_type
        """
        return self._plugin_base._entity_db_map[self._entity_type]

    @property
    def action_node_id(self):
        node_id = self._config.get(INSTANCE) or self.default_config()[INSTANCE]
        if not node_id:
            raise Exception('Error: can not contact node')
        return node_id

    def _get_entities_from_view(self, projection=None) -> Iterable[dict]:
        """
        Gets the relevant entities for this action from the view (using internal_axon_ids)
        :param projection: optional projection to the DB
        :return: Iterable
        """
        return iterate_axonius_entities(self._entity_type, self._internal_axon_ids,
                                        projection=projection)

    def _get_trigger_description(self):
        """
        Creates a readable message for the different actions.
        :return:
        """
        first_trigger = next(iter(self._triggered_set))
        first_trigger_data = getattr(self._run_configuration.conditions, first_trigger.name, '')
        return first_trigger.value.format(first_trigger_data)

    @staticmethod
    @abstractmethod
    def config_schema() -> dict:
        """
        The wanted schema from the config needed for the action
        """

    @staticmethod
    @abstractmethod
    def default_config() -> dict:
        """
        The default config to display to the user
        """

    def run(self) -> ActionRunResults:
        """
        Performs the given action.
        Should use the self._config, self._internal_axon_ids and over data provided
        """
        try:
            res = list(self._run())
            res_dict = {
                x.internal_axon_id: x
                for x
                in res
            }

            internal_axon_ids_set = set(self._internal_axon_ids)
            unexpected_entities = set(res_dict) - internal_axon_ids_set
            if unexpected_entities:
                logger.warning(f'Found unexpected entities in res: {unexpected_entities} for {type(self).__name__}')

            successful_entities = [EntityResult(x.internal_axon_id, x.successful, x.status)
                                   for x
                                   in res
                                   if x.successful and x.internal_axon_id in internal_axon_ids_set]

            unsuccessful_entities = [EntityResult(x.internal_axon_id, x.successful, x.status)
                                     for x
                                     in res
                                     if not x.successful and x.internal_axon_id in internal_axon_ids_set]

            for x in internal_axon_ids_set:
                if x not in res_dict:
                    unsuccessful_entities.append(EntityResult(x, False, 'Not reported back'))

            return ActionRunResults(successful_entities, unsuccessful_entities, '')
        except Exception as e:
            logger.exception(
                f'Error - {e} - performing action {type(self).__name__} with parameters '
                f'{self._triggered_set}')
            tb = ''.join(traceback.format_tb(e.__traceback__))
            return ActionRunResults([],
                                    [EntityResult(x, False, f'Error {e}') for x in self._internal_axon_ids],
                                    f'{str(e)}\n{tb}')

    @abstractmethod
    def _run(self) -> EntitiesResult:
        """
        See self.run
        """

    def _log_activity_tag_actions(self):
        self._plugin_base.log_activity(AuditCategory.Enforcements, AuditAction.TagUpdate, {
            'enforcement': self._report_data.get('name', '')
        }, AuditType.Info)
