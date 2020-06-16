import logging
import mimetypes
from email.utils import make_msgid
from typing import Iterable
import os
from jinja2 import Environment, FileSystemLoader

from axonius.consts.plugin_consts import GUI_SYSTEM_CONFIG_COLLECTION, GUI_PLUGIN_NAME

from axonius.consts.report_consts import LOGOS_PATH
from axonius.entities import EntityType
from axonius.logging.audit_helper import AuditAction, AuditCategory, AuditType

from axonius.utils import gui_helpers

from axonius.consts import report_consts
from axonius.types.enforcement_classes import AlertActionResult
from axonius.utils.db_querying_helper import perform_saved_view_converted, get_entities
from reports.action_types.action_type_alert import ActionTypeAlert

logger = logging.getLogger(f'axonius.{__name__}')
JINJA_ENV = Environment(loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), '../', 'templates', 'report')))


def __get_template(template_name):
    """
    Get the template with requested name, expected to be found in self.template_path and have the extension 'html'
    :param template_name: Name of template file
    :return: The template object
    """
    return JINJA_ENV.get_template(f'{template_name}.html')


REPORTS_TEMPLATES = {
    'report': __get_template('alert_report'),
    'calc_area': __get_template('report_calc_area'),
    'header': __get_template('report_header'),
    'second_header': __get_template('report_second_header'),
    'custom_body': __get_template('report_custom_body'),
    'table_section': __get_template('report_tables_section'),
    'adapter_image': __get_template('adapter_image'),
    'entity_name_url': __get_template('entity_name_url'),
    'table': __get_template('report_table'),
    'table_head': __get_template('report_table_head'),
    'table_row': __get_template('report_table_row'),
    'table_data': __get_template('report_table_data')
}


# pylint: disable=W0212
# This is oldcode, and these pylint disables come with that
# pylint: disable=R0914
# pylint: disable=R0915


class SendEmailsAction(ActionTypeAlert):
    """
    Sends an email
    """

    @staticmethod
    def config_schema() -> dict:
        return {
            'items': [
                {
                    'name': 'mailSubject',
                    'title': 'Email subject',
                    'type': 'string'
                },
                {
                    'name': 'emailBody',
                    'title': 'Custom message (up to 500 characters)',
                    'type': 'string',
                    'format': 'text',
                    'limit': 500
                },
                {
                    'name': 'emailList',
                    'title': 'Recipients',
                    'type': 'array',
                    'items': {
                        'type': 'string',
                        'format': 'email'
                    }
                },
                {
                    'name': 'emailListCC',
                    'title': 'Recipients CC',
                    'type': 'array',
                    'items': {
                        'type': 'string',
                        'format': 'email'
                    }
                },
                {
                    'name': 'sendDeviceCSV',
                    'title': 'Attach CSV with query results',
                    'type': 'bool'
                },
                {
                    'name': 'sendDevicesChangesCSV',
                    'title': 'Attach CSV with changes in query results',
                    'type': 'bool'
                }
            ],
            'required': [
                'emailList',
                'sendDeviceCSV',
                'sendDevicesChangesCSV'
            ],
            'type': 'array'
        }

    @staticmethod
    def default_config() -> dict:
        return {
            'mailSubject': '',
            'emailList': [],
            'emailListCC': [],
            'sendDevicesCSV': False,
            'sendDevicesChangesCSV': False,
            'emailBody': ''
        }

    # pylint: disable=too-many-branches
    # pylint: disable=E1101
    def _run(self) -> AlertActionResult:
        if not self._internal_axon_ids:
            return AlertActionResult(False, 'No Data')
        mail_sender = self._plugin_base.mail_sender
        if not mail_sender:
            logger.info('Email cannot be sent because no email server is configured')
            return AlertActionResult(False, 'Email is disabled')

        subject = self._config.get('mailSubject') if \
            self._config.get('mailSubject') else report_consts.REPORT_TITLE.format(name=self._report_data['name'],
                                                                                   query=self.trigger_view_name)
        logger.debug(self._config)
        if not self._config.get('emailList'):
            logger.info('Email cannot be sent because no recipients are configured')
            return AlertActionResult(False, 'Email required Recipients')
        email = mail_sender.new_email(subject,
                                      self._config['emailList'],
                                      cc_recipients=self._config.get('emailListCC', []))
        try:
            # all the trigger result
            if self._config.get('sendDeviceCSV', False):
                sort = gui_helpers.get_sort(self.trigger_view_config)
                field_list = self.trigger_view_config.get('fields', [
                    'specific_data.data.name', 'specific_data.data.hostname', 'specific_data.data.os.type',
                    'specific_data.data.last_used_users', 'labels'
                ])
                field_filters = self.trigger_view_config.get('colFilters', {})
                csv_string = gui_helpers.get_csv(self.trigger_view_parsed_filter,
                                                 sort,
                                                 {field: 1 for field in field_list},
                                                 self._entity_type,
                                                 field_filters=field_filters)

                email.add_attachment('Axonius Entity Data.csv', csv_string.getvalue().encode('utf-8'), 'text/csv')
        except Exception:
            logger.exception(f'Problem adding CSV attachment')

        added_result_count = 0
        removed_result_count = 0
        if self._added_axon_ids:
            added_result_count = len(self._added_axon_ids)
        if self._removed_axon_ids:
            removed_result_count = len(self._removed_axon_ids)

        try:
            if self._config.get('sendDevicesChangesCSV', False):
                if added_result_count:
                    self.__add_changes_csv(email, self._added_axon_ids, 'added')
                if removed_result_count:
                    self.__add_changes_csv(email, self._removed_axon_ids, 'removed')
        except Exception:
            logger.exception(f'Problem adding changes csv')

        image_cid = make_msgid()

        with open(f'{LOGOS_PATH}/logo/axonius.png', 'rb') as img:

            # know the Content-Type of the image
            maintype, subtype = mimetypes.guess_type(img.name)[0].split('/')

            # attach it
            email.add_logos_attachments(img.read(), maintype=maintype, subtype=subtype, cid=image_cid)

        reason = self._get_trigger_description()
        period = self.__get_period_description()

        html_sections = []
        prev_result_count = 0
        if self._run_configuration.result:
            prev_result_count = self._run_configuration.result_count

        query_link = self._generate_query_link()

        html_sections.append(REPORTS_TEMPLATES['header'].render({'subject': self._report_data['name']}))
        html_sections.append(REPORTS_TEMPLATES['second_header'].render(
            {'query_link': query_link, 'reason': reason, 'period': period, 'query': self.trigger_view_name}))
        if self._config.get('emailBody'):
            html_sections.append(REPORTS_TEMPLATES['custom_body'].render({
                'body_text': self._config['emailBody'].replace('\n', '\n<br>')
            }))
        html_sections.append(REPORTS_TEMPLATES['calc_area'].render({
            'prev': prev_result_count,
            'added': added_result_count,
            'removed': removed_result_count,
            'sum': len(self._internal_axon_ids)
        }))
        images_cid = {}
        projection = {
            'adapters': 1
        }
        if self._entity_type == EntityType.Devices:
            projection['specific_data.data.hostname'] = 1
        elif self._entity_type == EntityType.Users:
            projection['specific_data.data.username'] = 1

        if self.trigger_view_from_db:
            results = perform_saved_view_converted(self._entity_type, self.trigger_view_from_db, projection, limit=10)
        else:
            results = get_entities(10, 0, self._create_query(self._internal_axon_ids), {},
                                   projection, self._entity_type)

        self.__create_table_in_email(email, results, html_sections, images_cid, 'Top 10 results')
        if added_result_count > 0:
            results = get_entities(5, 0, self._create_query(self._added_axon_ids), {},
                                   projection, self._entity_type)
            self.__create_table_in_email(email, results, html_sections, images_cid,
                                         f'Top 5 new {self._entity_type} in query')
        if removed_result_count > 0:
            results = get_entities(5, 0, self._create_query(self._removed_axon_ids), {},
                                   projection, self._entity_type)

            self.__create_table_in_email(email, results, html_sections, images_cid,
                                         f'Top 5 {self._entity_type} removed from query')

        html_data = REPORTS_TEMPLATES['report'].render(
            {'query_link': query_link, 'image_cid': image_cid[1:-1], 'content': ''.join(html_sections)})

        email.send(html_data)
        self._plugin_base.log_activity(AuditCategory.Reports, AuditAction.Trigger, {
            'name': self._report_data['name']
        }, AuditType.Info)
        return AlertActionResult(True, 'Sent email')

    def __create_table_in_email(self, email, data: Iterable[dict], sections: list, images_cids: dict,
                                header: str):
        """
        Undocumented - migrated from reports/service.py
        :param email: the email instance
        :param data: the devices to send
        :param sections: list of html sections
        :param images_cids: images cids for the email html attachments
        :param header: of the section contains the table
        :return:
        """
        heads = [REPORTS_TEMPLATES['table_head'].render({'content': 'Adapters'}),
                 REPORTS_TEMPLATES['table_head'].render({'content': 'Host Name'})]

        rows = []
        for entity in data:
            item_values = []

            canonized_value = [str(x) for x in entity['adapters']]
            row_images = []
            for adapter in canonized_value:
                if adapter not in images_cids:

                    cid = make_msgid()
                    with open(f'{LOGOS_PATH}/logos/adapters/{adapter}.png',
                              'rb') as img:

                        # know the Content-Type of the image
                        maintype, subtype = mimetypes.guess_type(img.name)[0].split('/')

                        # attach it
                        email.add_logos_attachments(img.read(), maintype=maintype, subtype=subtype, cid=cid)
                    images_cids[adapter] = cid
                    row_images.append(cid)
                else:
                    row_images.append(images_cids[adapter])

            cid_template = []
            for img in row_images:
                cid_template.append(REPORTS_TEMPLATES['adapter_image'].render({'image_cid': img[1:-1]}))

            item_values.append(REPORTS_TEMPLATES['table_data'].render(
                {'content': '\n'.join(cid_template)}))
            entity_value = ''
            if self._entity_type == EntityType.Devices:
                entity_value = entity.get('specific_data.data.hostname', '')
            elif self._entity_type == EntityType.Users:
                entity_value = entity.get('specific_data.data.username', '')
            if isinstance(entity_value, list):
                canonized_value = [str(x) for x in entity_value]
                entity_value = ','.join(canonized_value)
            item_values.append(REPORTS_TEMPLATES['table_data'].render({
                'content': REPORTS_TEMPLATES['entity_name_url'].render({
                    'entity_link': self.__generate_entity_link(entity['internal_axon_id']),
                    'content': entity_value
                })}))
            rows.append(REPORTS_TEMPLATES['table_row'].render({'content': '\n'.join(item_values)}))
        sections.append(REPORTS_TEMPLATES['table_section'].render({
            'header': header,
            'content': REPORTS_TEMPLATES['table'].render({
                'head_content': REPORTS_TEMPLATES['table_row'].render({'content': '\n'.join(heads)}),
                'body_content': '\n'.join(rows)
            }),
        }))

    def __get_period_description(self):
        return self._run_configuration.period.value

    def __generate_entity_link(self, entity_id):
        # Getting system config from the gui.
        system_config = self._plugin_base._get_collection(GUI_SYSTEM_CONFIG_COLLECTION, GUI_PLUGIN_NAME).find_one(
            {'type': 'server'}) or {}
        return 'https://{}/{}/{}'.format(
            system_config.get('server_name', 'localhost'), self._entity_type.value, entity_id)

    def __add_changes_csv(self, email, trigger_data: list, data_action):
        """
        add csv attachment to the mail contains the changed values added or removed from the prev query
        :param email: the email instance
        :param trigger_data: The results difference added or removed list.
        :param data_action: added or removed from query
        """

        parsed_query_filter = self._create_query(trigger_data)
        field_list = self.trigger_view_config.get('fields', [
            'specific_data.data.name', 'specific_data.data.hostname', 'specific_data.data.os.type',
            'specific_data.data.last_used_users'
        ])
        sort = gui_helpers.get_sort(self.trigger_view_config)
        field_filters = self.trigger_view_config.get('colFilters', {})
        csv_string = gui_helpers.get_csv(parsed_query_filter, sort,
                                         {field: 1 for field in field_list},
                                         self._entity_type,
                                         field_filters=field_filters)

        email.add_attachment(f'Axonius {data_action} entity data.csv', csv_string.getvalue().encode('utf-8'),
                             'text/csv')
