import logging
import traceback
from abc import ABC, abstractmethod
from typing import Set, List

from axonius.entities import EntityType
from axonius.types.enforcement_classes import (Trigger, TriggeredReason,
                                               AlertActionResult, ActionRunResults, EntityResult)
from reports.action_types.action_type_base import ActionTypeBase

logger = logging.getLogger(f'axonius.{__name__}')


class ActionTypeAlert(ActionTypeBase, ABC):

    def __init__(self,
                 action_saved_name: str,
                 config,
                 run_configuration: Trigger,
                 report_data: dict, triggered_set: Set[TriggeredReason],
                 internal_axon_ids: List[str],
                 entity_type: EntityType,
                 added_axon_ids: List[str],
                 removed_axon_ids: List[str]):
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
                f'{self._triggered_set}, {self._config},')
            tb = ''.join(traceback.format_tb(e.__traceback__))
            return ActionRunResults([],
                                    [EntityResult(x, False, f'Error {e}') for x in self._internal_axon_ids],
                                    f'{str(e)}\n{tb}')

    @abstractmethod
    def _run(self) -> AlertActionResult:
        pass
