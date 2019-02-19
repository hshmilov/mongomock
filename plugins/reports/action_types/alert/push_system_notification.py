import logging

from axonius.consts import report_consts
from reports.enforcement_classes import EntityResult
from reports.action_types.action_type_alert import ActionTypeAlert

logger = logging.getLogger(f'axonius.{__name__}')


class SystemNotificationAction(ActionTypeAlert):
    """
    Pushes a new system notification
    """

    @staticmethod
    def config_schema() -> dict:
        return {
        }

    @staticmethod
    def default_config() -> dict:
        return {
        }

    def run(self) -> EntityResult:
        query_name = self._run_configuration.view.name
        title = report_consts.REPORT_TITLE.format(name=self._report_data['name'], query=query_name)

        old_results_num_of_devices = len(self._internal_axon_ids) + len(self._removed_axon_ids) - \
            len(self._added_axon_ids)

        content = report_consts.REPORT_CONTENT.format(name=self._report_data['name'],
                                                      query=query_name,
                                                      trigger_message=self._get_trigger_description(),
                                                      num_of_current_devices=len(self._internal_axon_ids),
                                                      old_results_num_of_devices=old_results_num_of_devices,
                                                      query_link=self._generate_query_link(query_name))

        result = self._plugin_base.create_notification(title, content)
        return EntityResult(bool(result), 'Created notification' if not result else 'Failed creating notification')
