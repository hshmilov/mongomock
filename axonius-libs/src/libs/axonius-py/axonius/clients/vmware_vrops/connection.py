import datetime
import logging

import pytz

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.clients.vmware_vrops.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES, TOKEN_URL, RESOURCES_URL, \
    DEFAULT_TIMEOUT_HOURS, ALERTS_URL, VIRTUAL_MACHINE_PROPERTIES_URL, PROPERTIES_URL, PROPERTIES_BLACK_LIST, \
    HOST_SYSTEM_PROPERTIES_URL, SECOND_PROPERTIES_URL, DEVICE_STATE_NOT_EXISTING
from axonius.utils.datetime import parse_date
from axonius.utils.parsing import int_or_none

logger = logging.getLogger(f'axonius.{__name__}')


class VmwareVropsConnection(RESTConnection):
    """ rest client for VmwareVrops adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='suite-api/api',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._token_timeout = None
        self._token = None

    def _set_token(self):
        now = datetime.datetime.utcnow()
        now = now.replace(tzinfo=pytz.UTC)
        if self._token_timeout and self._token_timeout > now:
            # Header is deleted for some reason, so we need to do this each time.
            self._session_headers['Authorization'] = f'vRealizeOpsToken {self._token}'
            return

        body_params = {
            'username': self._username,
            'password': self._password
        }
        response = self._post(TOKEN_URL, body_params=body_params)
        if not (isinstance(response, dict) and response.get('token')):
            raise RESTException(f'Response not in correct format: {response}')

        self._token = response.get('token')

        now = datetime.datetime.utcnow()
        now = now.replace(tzinfo=pytz.UTC)
        self._token_timeout = parse_date(response.get('expiresAt')) or (
            now + datetime.timedelta(hours=DEFAULT_TIMEOUT_HOURS))

        self._session_headers['Authorization'] = f'vRealizeOpsToken {self._token}'

    def _connect(self):
        if not (self._username and self._password):
            raise RESTException('No username or password')

        try:
            self._set_token()
            url_params = {'pageSize': 1}
            self._get(RESOURCES_URL, url_params=url_params)
        except Exception as e:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    def _get(self, *args, **kwargs):
        self._set_token()
        return super()._get(*args, **kwargs)

    def _get_alerts_by_resource_id(self):
        alerts_by_resource_id = {}
        try:
            url_params = {'pageSize': DEVICE_PER_PAGE}

            logger.info('Starting to fetch alerts.')
            response = self._get(ALERTS_URL, url_params=url_params)
            if not (isinstance(response, dict) and
                    isinstance(response.get('alerts'), list) and
                    isinstance(response.get('pageInfo'), dict)):
                logger.warning(f'Received invalid response for alerts: {response}')
                return alerts_by_resource_id

            page_info = response.get('pageInfo')

            total_count = int_or_none(page_info.get('totalCount')) or 0
            page_size = int_or_none(page_info.get('pageSize')) or 1
            number_of_pages = int(
                total_count / page_size) + 1  # Should add 1 to collect all the devices from the last page.

            for alert in response.get('alerts'):
                if not (isinstance(alert, dict) and alert.get('resourceId')):
                    continue
                alerts_by_resource_id.setdefault(alert.get('resourceId'), list()).append(alert)

            for page_number in range(1, number_of_pages):
                url_params['page'] = page_number
                response = self._get(ALERTS_URL, url_params=url_params)

                if not (isinstance(response, dict) and
                        isinstance(response.get('alerts'), list)):
                    logger.warning(f'Received invalid response for alerts in page {page_number}: {response}')
                    continue

                for alert in response.get('alerts'):
                    if not (isinstance(alert, dict) and alert.get('resourceId')):
                        continue
                    alerts_by_resource_id.setdefault(alert.get('resourceId'), list()).append(alert)
        except Exception:
            logger.exception(f'Invalid request made while paginating alerts')

        logger.info('Finished fetching alerts.')
        return alerts_by_resource_id

    def _get_properties_types(self):
        response = self._get(VIRTUAL_MACHINE_PROPERTIES_URL)
        if not (isinstance(response, dict) and isinstance(response.get('resourceTypeAttributes'), list)):
            logger.error(f'Response not in correct format {response}')
            return None
        properties = [property_type.get('key') for property_type in response.get('resourceTypeAttributes') if
                      property_type.get('key')]

        response = self._get(HOST_SYSTEM_PROPERTIES_URL)
        if not (isinstance(response, dict) and isinstance(response.get('resourceTypeAttributes'), list)):
            logger.error(f'Response not in correct format {response}')
            return None

        properties.extend([property_type.get('key') for property_type in response.get('resourceTypeAttributes') if
                           property_type.get('key')])
        for property_type in PROPERTIES_BLACK_LIST:
            if property_type in properties:
                properties.remove(property_type)

        return properties

    def _get_properties_by_resource_id(self, resource_ids, properties):
        properties_by_resource_id = {}
        try:
            response = self._post(PROPERTIES_URL, body_params={'resourceIds': resource_ids,
                                                               'propertyKeys': properties})
            if not (isinstance(response, dict) and
                    isinstance(response.get('values'), list)):
                logger.error(f'Response not in correct format {response}')
                return properties_by_resource_id

            second_properties = self._get_second_properties(resource_ids)

            for resource_property in response.get('values'):
                if not (isinstance(resource_property, dict) and
                        isinstance(resource_property.get('property-contents'), dict) and
                        resource_property.get('resourceId')):
                    logger.warning(f'Resource property not in correct format {resource_property}')
                    continue

                resource_properties = self._get_properties_as_dict(
                    resource_property.get('property-contents').get('property-content'))

                resource_properties.update(second_properties.get(resource_property.get('resourceId')))
                properties_by_resource_id[resource_property.get('resourceId')] = resource_properties
        except Exception as e:
            logger.exception(
                f'Invalid request made while getting properties, resource ids: {resource_ids},'
                f' property keys: {properties}')
        return properties_by_resource_id

    @staticmethod
    def _get_second_properties_as_a_dict(properties):
        return {resource_property.get('name'): resource_property.get('value') for resource_property in properties if
                resource_property.get('name') is not None}

    def _get_second_properties(self, resource_ids):
        properties_by_resource_id = {}
        try:
            url_params = {'resourceId': resource_ids}
            response = self._get(SECOND_PROPERTIES_URL, url_params=url_params)
            if not (isinstance(response, dict) and
                    isinstance(response.get('resourcePropertiesList'), list)):
                logger.error(f'Response not in correct format {response}')
                return properties_by_resource_id

            for resource_property in response.get('resourcePropertiesList'):
                if not (isinstance(resource_property, dict) and
                        isinstance(resource_property.get('property'), list) and
                        resource_property.get('resourceId')):
                    continue

                resource_id = resource_property.get('resourceId')
                properties_by_resource_id[resource_id] = self._get_second_properties_as_a_dict(
                    resource_property.get('property'))

        except Exception as e:
            logger.exception(
                f'Invalid request made while getting properties, resource ids: {resource_ids}')
        return properties_by_resource_id

    @staticmethod
    def _get_properties_as_dict(properties):
        properties_as_dict = {}
        for resource_property in properties:
            if not resource_property.get('statKey'):
                continue
            if resource_property.get('data') is not None:
                properties_as_dict[resource_property.get('statKey')] = resource_property.get('data')

            elif resource_property.get('values') is not None:
                properties_as_dict[resource_property.get('statKey')] = resource_property.get('values')
        return properties_as_dict

    # pylint: disable=too-many-branches
    def _paginated_device_get(self, ignore_not_existing_devices: bool=True):
        try:
            total_fetched_devices = 0
            alerts_by_resource_id = self._get_alerts_by_resource_id()
            properties = self._get_properties_types()

            url_params = {'pageSize': DEVICE_PER_PAGE, 'resourceKind': ['virtualmachine', 'hostsystem']}

            response = self._get(RESOURCES_URL, url_params=url_params)
            if not (isinstance(response, dict) and
                    isinstance(response.get('resourceList'), list) and
                    isinstance(response.get('pageInfo'), dict)):
                logger.warning(f'Received invalid response for devices: {response}')
                return

            page_info = response.get('pageInfo')

            if MAX_NUMBER_OF_DEVICES <= (int_or_none(page_info.get('totalCount')) or 0):
                logger.info(
                    f'number of devices is {page_info.get("totalCount")} and is cut off to {MAX_NUMBER_OF_DEVICES}.')
            number_of_devices = min(int_or_none(page_info.get('totalCount')) or 0, MAX_NUMBER_OF_DEVICES)

            number_of_pages = int(number_of_devices / int_or_none(page_info.get('pageSize')) or 1) + 1

            resource_ids = [resource.get('identifier') for resource in response.get('resourceList') if
                            resource.get('identifier')]
            properties_by_resource_id = self._get_properties_by_resource_id(resource_ids, properties)

            for resource in response.get('resourceList'):
                if not isinstance(resource, dict):
                    continue
                if ignore_not_existing_devices and not self._is_existing_device(resource):
                    continue
                resource['extra_alerts'] = alerts_by_resource_id.get(resource.get('identifier'))
                resource['extra_properties'] = properties_by_resource_id.get(resource.get('identifier'))
                yield resource
                total_fetched_devices += 1
                if total_fetched_devices >= MAX_NUMBER_OF_DEVICES:
                    break

            for page_number in range(1, number_of_pages):
                url_params['page'] = page_number
                response = self._get(RESOURCES_URL, url_params=url_params)

                if not (isinstance(response, dict) and
                        isinstance(response.get('resourceList'), list)):
                    logger.warning(f'Received invalid response for devices in page {page_number}: {response}')
                    continue

                resource_ids = [resource.get('identifier') for resource in response.get('resourceList') if
                                resource.get('identifier')]
                properties_by_resource_id = self._get_properties_by_resource_id(resource_ids, properties)

                for resource in response.get('resourceList'):
                    if not isinstance(resource, dict):
                        continue
                    if ignore_not_existing_devices and not self._is_existing_device(resource):
                        continue
                    resource['extra_alerts'] = alerts_by_resource_id.get(resource.get('identifier'))
                    resource['extra_properties'] = properties_by_resource_id.get(resource.get('identifier'))
                    yield resource
                    total_fetched_devices += 1
                    if total_fetched_devices >= MAX_NUMBER_OF_DEVICES:
                        break

            logger.info(f'Got total of {total_fetched_devices} devices')
        except Exception:
            logger.exception(f'Invalid request made while paginating devices')
            raise

    @staticmethod
    def _is_existing_device(device_raw):
        resource_status_states = device_raw.get('resourceStatusStates')
        if not isinstance(resource_status_states, list):
            return True
        for resource_status_state in resource_status_states:
            if not isinstance(resource_status_state, dict):
                continue
            resource_state = resource_status_state.get('resourceState')
            if (isinstance(resource_state, str) and
                    resource_state.lower() == DEVICE_STATE_NOT_EXISTING):
                logger.debug(f'Ignoring NOT_EXISTING device,'
                             f' id: {device_raw.get("identifier")},'
                             f' resourceKey: {device_raw.get("resourceKey")},'
                             f' resourceStatusStates: {resource_status_states}')
                return False
        return True

    # pylint: disable=arguments-differ
    def get_device_list(self, ignore_not_existing_devices: bool=True):
        try:
            yield from self._paginated_device_get(ignore_not_existing_devices=ignore_not_existing_devices)
        except RESTException as err:
            logger.exception(str(err))
            raise
