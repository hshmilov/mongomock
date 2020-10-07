import logging

from typing import List, Iterable, Generator

from axonius.clients.dns_made_easy.consts import ADAPTER_NAME, API_ENDPOINT_BASE
from axonius.clients.dns_made_easy.connection import DnsMadeEasyConnection
from axonius.types.enforcement_classes import EntityResult
from axonius.utils.parsing import int_or_none, parse_bool_from_raw
from reports.action_types.action_type_base import ActionTypeBase, \
    generic_fail, add_node_selection, add_node_default


logger = logging.getLogger(f'axonius.{__name__}')


class RemoveSubdomainFromDNSME(ActionTypeBase):
    @staticmethod
    def config_schema() -> dict:
        schema = {
            'items': [
                {
                    'name': 'use_adapter',
                    'title': 'Use stored credentials from the DNS Made Easy adapter',
                    'type': 'bool',
                    'default': False
                },
                {
                    'name': 'domain',
                    'title': 'Host name or IP address',
                    'type': 'string',
                    'default': API_ENDPOINT_BASE
                },
                {
                    'name': 'api_key',
                    'title': 'API key',
                    'type': 'string'
                },
                {
                    'name': 'secret_key',
                    'title': 'Secret key',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'verify_ssl',
                    'title': 'Verify SSL',
                    'type': 'bool',
                    'default': False
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS proxy',
                    'type': 'string'
                },
                {
                    'name': 'proxy_username',
                    'title': 'HTTPS proxy user name',
                    'type': 'string'
                },
                {
                    'name': 'proxy_password',
                    'title': 'HTTPS proxy password',
                    'type': 'string',
                    'format': 'password'
                }
            ],
            'required': [
                'use_adapter',
                'verify_ssl'
            ],
            'type': 'array'
        }
        # enable the pop-up in the EC action for Core/Node
        return add_node_selection(config_schema=schema)

    @staticmethod
    def default_config() -> dict:
        return add_node_default({
            'use_adapter': False,
            'domain': API_ENDPOINT_BASE,
            'api_key': None,
            'secret_key': None,
            'verify_ssl': False,
            'https_proxy': None,
            'proxy_username': None,
            'proxy_password': None,
        })

    @staticmethod
    def process_query_data(query_results: Iterable[dict]) -> Generator[dict, None, None]:
        """
        Take the passed query results acquired from an EC trigger query and
        extract the axonius internal ID, domain ID and record ID from that
        data and yield it to the calling function.

        :param query_results: An iterable dictionary of data from an EC
        trigger query.
        :yield entity_data: a dictionary containing 3 values; the internal
        axonius ID, the domain ID and the record ID.
        """
        for result in query_results:
            internal_axon_id = result.get('internal_axon_id')
            if not isinstance(internal_axon_id, str):
                logger.warning(f'Malformed internal axonius ID. Expected a '
                               f'str, got {type(internal_axon_id)}: '
                               f'{str(internal_axon_id)}')
                continue

            adapters = result.get('adapters')
            if not isinstance(adapters, list):
                logger.warning(f'Malformed adapters data. Expected a list, got '
                               f'{type(adapters)}: {str(adapters)}')
                continue

            for adapter in adapters:
                if not isinstance(adapter, dict):
                    logger.warning(f'Malformed adapter. Expected a dict, '
                                   f'got {type(adapter)}: {str(adapter)}')
                    continue

                adapter_data = adapter.get('data')
                if not isinstance(adapter_data, dict):
                    logger.warning(f'Malformed adapter data. Expected a dict, '
                                   f'got {type(adapter_data)}: {str(adapter_data)}')
                    continue

                record_id = int_or_none(adapter_data.get('record_id'))
                if not isinstance(record_id, int):
                    logger.warning(f'Malformed record ID. Expected an int, got '
                                   f'{type(record_id)}: {str(record_id)}')
                    continue

                # using domain_id here rather than dnsme_domain since the name
                #    fits better with the intent of the variable and the usage
                #    in the API documentation
                domain_id = int_or_none(adapter_data.get('dnsme_domain').get('dnsme_id'))
                if not isinstance(domain_id, int):
                    logger.warning(f'Malformed domain ID. Expected and int, got '
                                   f'{type(domain_id)}: {str(domain_id)}')
                    continue

                entity_data = {
                    'internal_axon_id': internal_axon_id,
                    'record_id': record_id,
                    'domain_id': domain_id
                }

                yield entity_data

    # pylint: disable=protected-access, too-many-branches, too-many-statements
    def _run(self) -> List[EntityResult]:
        """
        This function pulls data that matches an EC query from the chosen
        adapter, passes the data to be processed, then takes the data
        yielded from the processing in or to delete a subdomain from the
        managed service. A subdomain is a DEVICE in this adapter.
        """
        results = list()
        try:
            # get the adapter name
            adapter_unique_name = self._plugin_base._get_adapter_unique_name(
                ADAPTER_NAME,
                self.action_node_id
            )
            if not isinstance(adapter_unique_name, str):
                message = f'Malformed adapter name. Expected a string, got ' \
                          f'{type(adapter_unique_name)}: {str(adapter_unique_name)}'
                logger.warning(message)
                raise ValueError(message)

            # leave this madness if there is no data
            if not self._internal_axon_ids:
                return (yield from generic_fail(adapter_unique_name,
                                                'No data...'))

            # get interesting fields from the db to be used in process_query_data()
            # the call to delete a domain record requires only the domain ID and
            #    the record ID
            query_results = self._get_entities_from_view({
                'internal_axon_id': 1,
                'adapters.data.dnsme_domain.dnsme_id': 1,  # this is the domain ID
                'adapters.data.record_id': 1,  # this is the record ID
            })
            if not isinstance(query_results, Iterable):
                message = f'Malformed query results. Expected an iterable, ' \
                          f'got {type(query_results)}: {str(query_results)}'
                logger.warning(message)
                raise ValueError(message)

            data_dict = self.process_query_data(query_results)
            if not isinstance(data_dict, Generator):
                message = f'Malformed query data. Expected an iterable, got ' \
                          f'{type(data_dict)}: {str(data_dict)}'
                logger.warning(message)
                raise ValueError(message)

            for device in data_dict:
                if not isinstance(device, dict):
                    message = f'Malformed device. Expected a dict, got ' \
                              f'{type(device)}: {str(device)}'
                    logger.warning(message)
                    raise ValueError(message)

                # make the call to delete_device_in dns_made_easy/service.py
                if parse_bool_from_raw(self._config.get('use_adapter')) is True:
                    logger.info(
                        f'Started deleting device {device.get("record_id")} '
                        f'from {device.get("domain_id")} in Adapter Mode')
                    try:
                        response = self._plugin_base.request_remote_plugin(
                            resource='remove_subdomain_from_dns_made_easy',
                            plugin_unique_name=adapter_unique_name,
                            method='POST',
                            json=device
                        )

                        if response is None:
                            message = f'Unable to create DNS Made Easy client' \
                                      f' using the adapter config'
                            logger.exception(message)
                            raise ValueError(message)

                        if response.status_code != 200:
                            message = f'Unexpected Error: {str(response.text)}'
                            logger.warning(message)
                            results.append(EntityResult(
                                device.get('internal_axon_id'),
                                False,
                                message))

                        logger.info(
                            f'Finished deleting device {device.get("record_id")} '
                            f'in Adapter Mode')

                        results.append(EntityResult(
                            device.get('internal_axon_id'),
                            True,
                            f'Removal of {device.get("record_id")} from '
                            f'{device.get("domain_id")} successful'))

                    except Exception:
                        message = f'Unable to create the connection to DNS ' \
                                  f'Made Easy. Please contact Axonius Support.'
                        logger.exception(message)
                        results.append(EntityResult(
                            device.get('internal_axon_id'),
                            False,
                            f'Unexpected Error: {str(message)}'))

                else:
                    # run normally
                    logger.info(
                        f'Started deleting device {device.get("record_id")} '
                        f'from {device.get("domain_id")}in EC Mode')

                    if not (self._config.get('domain') and
                            self._config.get('api_key') and
                            self._config.get('secret_key')
                            ):
                        return (yield from generic_fail(
                            internal_axon_ids=self._internal_axon_ids,
                            reason='Missing parameters for connection'))
                    try:
                        # create a new connection. these are extremely short-lived
                        connection = DnsMadeEasyConnection(
                            domain=self._config.get('domain'),
                            apikey=self._config.get('api_key'),
                            secret_key=self._config.get('secret_key'),
                            verify_ssl=self._config.get('verify_ssl'),
                            https_proxy=self._config.get('https_proxy'),
                            proxy_username=self._config.get('proxy_username'),
                            proxy_password=self._config.get('proxy_password')
                        )
                    except Exception as err:
                        logger.exception(f'Unable to create DNS Made Easy '
                                         f'client: {str(err)}')
                        raise

                    try:
                        if not isinstance(connection, DnsMadeEasyConnection):
                            message = f'Unable to create the connection to ' \
                                      f'DNS Made Easy. Please contact Axonius ' \
                                      f'Support.'
                            logger.warning(message)
                            results.append(EntityResult(
                                device.get('internal_axon_id'),
                                False,
                                f'Unexpected Error: {str(message)}'))

                        with connection:
                            status, error_message = \
                                connection.remove_subdomain_from_dns_made_easy(
                                    device=device
                                )

                            if not status:
                                message = f'Unexpected Error: ' \
                                          f'{str(error_message)}'
                                logger.warning(message)
                                results.append(EntityResult(
                                    device.get('internal_axon_id'),
                                    False,
                                    message))
                                continue

                            logger.info(
                                f'Finished deleting device '
                                f'{device.get("record_id")} in EC Mode')
                            results.append(EntityResult(
                                device.get('internal_axon_id'),
                                True,
                                f'Removal of {device.get("record_id")} from '
                                f'{device.get("domain_id")} successful'))
                    except Exception:
                        message = 'Unable to delete devices'
                        logger.exception(message)
                        results.append(EntityResult(
                            device.get('internal_axon_id'),
                            False,
                            f'Unexpected Error: {str(message)}'))
        except Exception:
            logger.exception(f'Problem with enforcement center action')
            results.append(EntityResult(str(self._internal_axon_ids),
                                        False,
                                        f'Unexpected error during EC action'))

        return (yield from results)
