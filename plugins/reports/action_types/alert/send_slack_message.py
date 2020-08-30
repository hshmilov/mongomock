import logging
import requests
from tabulate import tabulate

from axonius.utils import gui_helpers, db_querying_helper
from axonius.types.enforcement_classes import AlertActionResult
from reports.action_types.action_type_alert import ActionTypeAlert

logger = logging.getLogger(f'axonius.{__name__}')

NUMBER_OF_RESULT = 20
DEFAULT_QUERY_MESSAGE = 'All Entities'
# minimum amount of entity fields, apart from Adapters, needed to display a result
MIN_FIELD_COUNT = 1
REQUEST_TIMEOUT = 10
CHAR_LIMIT = 3500
JSON_DISPLAY = 'JSON'
TABLE_DISPLAY = 'Table'


# pylint: disable=logging-format-interpolation


class SlackSendMessageAction(ActionTypeAlert):
    """
    Send a message to Slack channel
    """

    @staticmethod
    def config_schema() -> dict:
        return {
            'items': [
                {
                    'name': 'webhook_url',
                    'title': 'Incoming webhook URL',
                    'type': 'string'
                },
                {
                    'name': 'verify_url',
                    'title': 'Verify URL',
                    'type': 'bool'
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS proxy',
                    'type': 'string'
                },
                {
                    'name': 'incident_description',
                    'title': 'Incident description',
                    'type': 'string',
                    'format': 'text'
                },
                {
                    'name': 'display',
                    'title': 'Results display format',
                    'type': 'string',
                    'enum': [JSON_DISPLAY, TABLE_DISPLAY],
                    'default': JSON_DISPLAY
                }
            ],
            'required': [
                'incident_description',
                'verify_url',
                'webhook_url',
                'display'
            ],
            'type': 'array'
        }

    @staticmethod
    def default_config() -> dict:
        return {
            'incident_description': None,
            'verify_url': False,
            'webhook_url': None,
            'https_proxy': None,
            'display': JSON_DISPLAY
        }

    # pylint: disable=too-many-statements
    @staticmethod
    def _entity_to_list(entity: dict, i: int) -> list:
        """ Convert entity to list in order defined by headers dict:
         Result number, Adapters, Asset Name, Host Name, OS Type, IP Address, Mac Address """

        def append_str_field(entity: dict, field: str, label: str, count: int) -> int:
            try:
                entity_list.append(entity.get(field))
                return count + 1 if entity.get(field) else count
            except Exception:
                entity_list.append(None)
                logger.warning(f'Failed getting {label} for entity {i}')
                return count

        def add_elem(lst: list, value):
            if isinstance(value, list):
                lst.extend(value)
            elif isinstance(value, str):
                lst.append(value)

        entity_list = []
        ips_list = []
        mac_list = []
        field_count = 0
        entity_list.append(str(i))
        if entity.get('adapters'):
            entity_list.append('\n'.join(entity.get('adapters')))
        else:
            logger.warning(f'Failed getting adapter names for entity {i}, no information can be displayed')
            return []

        field_count = append_str_field(entity, 'specific_data.data.name', 'asset name', field_count)
        field_count = append_str_field(entity, 'specific_data.data.hostname', 'host name', field_count)
        field_count = append_str_field(entity, 'specific_data.data.os.type', 'OS type', field_count)

        try:
            ips = entity.get('specific_data.data.network_interfaces.ips')
            add_elem(ips_list, ips)
            mac = entity.get('specific_data.data.network_interfaces.mac')
            add_elem(mac_list, mac)
        except Exception as e:
            logger.warning(f'Failed getting network interface for entity {i}')

        if isinstance(entity.get('specific_data.data.public_ips'), list):
            ips_list.extend(entity.get('specific_data.data.public_ips'))
        elif isinstance(entity.get('specific_data.data.public_ips'), str):
            ips_list.append(entity.get('specific_data.data.public_ips'))
        ips_list = list(set(ips_list))
        try:
            entity_list.append('\n'.join(ips_list))
            if ips_list:
                field_count += 1
        except Exception:
            entity_list.append(None)
            logger.warning(f'Failed getting IPs for entity {i}')

        try:
            entity_list.append('\n'.join(mac_list))
            if mac_list:
                field_count += 1
        except Exception:
            entity_list.append(None)
            logger.warning(f'Failed getting mac address for entity {i}')

        if field_count < MIN_FIELD_COUNT:
            return []

        return entity_list

    @staticmethod
    def _split_table(table: str) -> list:
        """ Split a table string into a list of table strings meeting the Slack message character limit """

        line_list = table.split('\n')
        table_string = ''
        tables_list = []
        char_count = 0
        for line in line_list:
            char_count += len(line)
            if char_count > CHAR_LIMIT:
                tables_list.append(table_string)
                table_string = f'{line}\n'
                char_count = len(line)
            else:
                table_string += f'{line}\n'

        tables_list.append(table_string)
        return tables_list

    # pylint: disable=too-many-locals, too-many-branches
    def _run(self) -> AlertActionResult:
        if not self._internal_axon_ids:
            return AlertActionResult(False, 'No Data')

        # Assign a value for already existing Actions who doesnt resaved the Action
        self._config['display'] = self._config.get('display') or JSON_DISPLAY

        fields_to_get = ['specific_data.data.name', 'specific_data.data.hostname', 'specific_data.data.os.type',
                         'specific_data.data.last_used_users', 'labels']
        if self._config.get('display') == TABLE_DISPLAY:
            fields_to_get.append('specific_data.data.network_interfaces')
            fields_to_get.append('specific_data.data.public_ips')

        field_list = self.trigger_view_config.get('fields', fields_to_get)
        sort = gui_helpers.get_sort(self.trigger_view_config)
        col_filters = self.trigger_view_config.get('colFilters', {})
        excluded_adapters = self.trigger_view_config.get('colExcludedAdapters', {})
        all_gui_entities = db_querying_helper.get_entities(None,
                                                           None,
                                                           self.trigger_view_parsed_filter,
                                                           sort, {
                                                               field: 1
                                                               for field
                                                               in field_list
                                                           },
                                                           self._entity_type,
                                                           field_filters=col_filters,
                                                           excluded_adapters=excluded_adapters)[0]

        if self._config.get('display') == JSON_DISPLAY:
            entities_str = ''
            for i, entity in enumerate(all_gui_entities):
                entities_str += str(entity) + '\n\n'
                if i == 4:  # Count start from 0
                    break
            old_results_num_of_devices = len(self._internal_axon_ids) + len(self._removed_axon_ids) - len(
                self._added_axon_ids)

        elif self._config.get('display') == TABLE_DISPLAY:
            # First column is Results, denoted by numbered cell
            headers = ['', 'Adapters', 'Asset Name', 'Host Name', 'OS Type', 'IP Address', 'MAC Address']
            entities_list = []
            count = 1
            for entity in all_gui_entities:
                entity_list = self._entity_to_list(entity, count)
                if entity_list:
                    entities_list.append(entity_list)
                    count += 1

                if count == NUMBER_OF_RESULT + 1:
                    break

            entities_table = tabulate(entities_list, headers, tablefmt='fancy_grid')

        alert_name = self._report_data['name']
        log_message_full = self._config['incident_description']
        proxies = {}
        if self._config.get('https_proxy') is not None and isinstance(self._config.get('https_proxy'), str):
            proxies['https'] = self._config.get('https_proxy').strip()
        proxy_message = f'HTTPS Proxy: {proxies.get("https")}\n' if proxies.get('https') else ''
        success = False
        try:
            if self._config.get('display') == JSON_DISPLAY:
                slack_dict = {
                    'attachments': [
                        {
                            'color': '#fd662c',
                            'text': 'Description: ' + log_message_full + '\n' + 'First 5 Results Are:\n' + entities_str,
                            'pretext': f'An Axonius alert - "{alert_name}" was triggered '
                                       f'because of {self._get_trigger_description()}.',
                            'title': f'Query "{self.trigger_view_name}"',
                            'title_link': self._generate_query_link(),
                            'fields': [
                                {
                                    'title': 'Current amount',
                                    'value': len(self._internal_axon_ids),
                                    'short': True
                                },
                                {
                                    'title': 'Previous amount',
                                    'value': old_results_num_of_devices,
                                    'short': True
                                }
                            ],
                            'footer': 'Axonius',
                            'footer_icon': 'https://s3.us-east-2.amazonaws.com/axonius-public/logo.png'
                        }
                    ]
                }

            elif self._config.get('display') == TABLE_DISPLAY:
                slack_dict = {
                    'text': f'An Axonius alert - "{alert_name}" was triggered '
                            f'because of {self._get_trigger_description()}.\n' +
                            f'<{self._generate_query_link()}|Query '
                            f'"{self.trigger_view_name or DEFAULT_QUERY_MESSAGE}">\n' +
                            f'Description: {log_message_full}\n' +
                            f'{proxy_message}'
                            f'First {NUMBER_OF_RESULT} Results Are:'
                }

            response = requests.post(url=self._config['webhook_url'],
                                     json=slack_dict,
                                     headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
                                     timeout=REQUEST_TIMEOUT,
                                     verify=self._config['verify_url'],
                                     proxies=proxies)
            success = response.status_code == 200
            message = 'Success' if success else str(response.text)

            if self._config.get('display') == TABLE_DISPLAY:
                message = 'Success' if success else str(response.content)
                for table in self._split_table(entities_table):
                    slack_dict = {
                        'text': f'```{table}```'
                    }
                    response = requests.post(url=self._config['webhook_url'],
                                             json=slack_dict,
                                             headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
                                             timeout=REQUEST_TIMEOUT,
                                             verify=self._config['verify_url'],
                                             proxies=proxies)
        except Exception as e:
            logger.exception('Problem sending to slack')
            message = str(e)

        return AlertActionResult(success, message)
