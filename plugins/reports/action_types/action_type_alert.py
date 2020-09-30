import logging
import traceback
from abc import ABC, abstractmethod
from typing import Set, List
import urllib.parse
from bson import ObjectId

from axonius.entities import EntityType
from axonius.types.enforcement_classes import (Trigger, TriggeredReason,
                                               AlertActionResult, ActionRunResults, EntityResult)
from axonius.utils.axonius_query_language import parse_filter
from axonius.consts.plugin_consts import GUI_SYSTEM_CONFIG_COLLECTION, GUI_PLUGIN_NAME
from axonius.utils.mongo_escaping import unescape_dict
from reports.action_types.action_type_base import ActionTypeBase

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=W0212, too-many-arguments


class ActionTypeAlert(ActionTypeBase, ABC):

    def __init__(self,
                 action_saved_name: str,
                 config,
                 run_configuration: Trigger,
                 report_data: dict, triggered_set: Set[TriggeredReason],
                 internal_axon_ids: List[str],
                 entity_type: EntityType,
                 added_axon_ids: List[str],
                 removed_axon_ids: List[str],
                 manual_input: dict = None):
        """
        CTOR
        :param action_saved_name: see ActionTypeBase
        :param config: see ActionTypeBase
        :param run_configuration: see ActionTypeBase
        :param report_data: see ActionTypeBase
        :param triggered_set: see ActionTypeBase
        :param internal_axon_ids: All internal axon ids in the query
        :param entity_type: see ActionTypeBase
        :param added_axon_ids: only new internal axon ids
        :param removed_axon_ids: only removed internal axon ids
        """
        ActionTypeBase.__init__(self, action_saved_name, config, run_configuration, report_data, triggered_set,
                                internal_axon_ids, entity_type)
        self._added_axon_ids = added_axon_ids
        self._removed_axon_ids = removed_axon_ids
        self._manual_input = manual_input

    def run(self) -> ActionRunResults:
        """
        This is ran when a trigger jumps
        """
        try:
            result = self._run()
            if result.successful:
                return ActionRunResults([EntityResult(x, True, result.status) for x in self._internal_axon_ids],
                                        [],
                                        None)
            return ActionRunResults([],
                                    [EntityResult(x, False, result.status) for x in self._internal_axon_ids],
                                    result.status)
        except Exception as e:
            logger.exception(
                f'Error - {e} - performing action {type(self).__name__} with parameters '
                f'{self._triggered_set}')
            tb = ''.join(traceback.format_tb(e.__traceback__))
            return ActionRunResults([],
                                    [EntityResult(x, False, f'Error {e}') for x in self._internal_axon_ids],
                                    f'{str(e)}\n{tb}')

    @abstractmethod
    def _run(self) -> AlertActionResult:
        pass

    @staticmethod
    def _create_query(trigger_data: list):
        """
        create the query for the result diff
        :param trigger_data:  The results difference added or removed result
        :return:
        """
        return {'internal_axon_id': {'$in': trigger_data}}

    @property
    def trigger_view_from_db(self) -> dict:
        """
        Fetch the view defining the action's trigger, from db according to its EntityType
        :return: Found document or empty dict if none exists
        """
        if not self._run_configuration.view.id:
            return {}
        return self._plugin_base.gui_dbs.entity_query_views_db_map[self._entity_type].find_one({
            '_id': ObjectId(self._run_configuration.view.id)
        })

    @property
    def trigger_view_name(self) -> str:
        """
        :return: Name of the trigger's view or None if none exists
        """
        return self.trigger_view_from_db.get('name')

    @property
    def trigger_view_config(self) -> dict:
        """
        :return: View configuration of the trigger's view or empty dict if none exists
        """
        if self._manual_input and self._manual_input.get('view'):
            return unescape_dict(self._manual_input['view'])
        return self.trigger_view_from_db.get('view', {})

    @property
    def trigger_view_parsed_filter(self) -> dict:
        """
        Parse the filter of the trigger's view or make a query over action's internal_axon_ids
        :return: A mongo query object valid for the entities collection
        """
        if self.trigger_view_config.get('query'):
            return parse_filter(self.trigger_view_config['query']['filter'], entity=self._entity_type)
        return self._create_query(self._internal_axon_ids)

    def _generate_query_link(self):
        # Getting system config from the gui.
        system_config = self._plugin_base._get_collection(GUI_SYSTEM_CONFIG_COLLECTION, GUI_PLUGIN_NAME).find_one(
            {'type': 'server'}) or {}
        url_params = urllib.parse.urlencode({'view': self.trigger_view_name})
        return 'https://{}/{}?{}'.format(
            system_config.get('server_name', 'localhost'), self._entity_type.value, url_params)
