import logging
import xmltodict

from urllib3.util.url import parse_url
# pylint: disable=import-error
from gvm.protocols.latest import Gmp
from gvm.connections import TLSConnection, SSHConnection
from openvas_adapter.consts import GvmProtocols, MAX_NUMBER_OF_DEVICES, DEVICE_PER_PAGE
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class OpenvasConnection(RESTConnection):
    """ python-gvm client for OpenVAS adapter """

    def __init__(self,
                 domain,
                 username,
                 password,
                 *args,
                 protocol: GvmProtocols = GvmProtocols.TLS,
                 port: int = None,
                 ssh_username: str = None,
                 ssh_password: str = None,
                 **kwargs,):
        """
        Create a new OpenVas Connection.
        :param domain: hostname
        :param username: username for openvas auth
        :param password: password for openvas auth
        :param protocol: protocol to connect with. Use a ``GvmProtocol` enum member.
                         Default: TLS
        :param port: Port to connect to. Default 22 for ssh and 9390 for tls
        :param ssh_username: username for ssh connection
        :param ssh_password: password for ssh connection
        :param kwargs:
        """
        self._protocol = protocol
        if protocol == GvmProtocols.SSH and not (ssh_username and ssh_password):
            raise ConnectionError('Please supply both username and password for SSH connection.')
        self.__debug_file_assets = kwargs.pop('_debug_file_assets', None)
        self.__debug_file_scans = kwargs.pop('_debug_file_scans', None)
        # parse host in case it's a URL and not just IP
        host = parse_url(domain).host
        super().__init__(
            *args,
            domain=host,
            username=username,
            password=password,
            port=port or protocol.value,
            url_base_prefix='',
            **kwargs
        )
        self._ssh_username = ssh_username
        self._ssh_password = ssh_password
        self._gvm_session = None
        self._gvm_conn = None

    @staticmethod
    def _transform(xml_input):
        response = xmltodict.parse(xml_input)
        response_root = list(response.keys())[0]
        return response[response_root]

    def connect(self):
        self.check_for_collision_safe()
        return self._connect()

    def _connect(self):
        # required by abstract class
        if self._protocol == GvmProtocols.SSH:
            self._gvm_conn = SSHConnection(
                hostname=self._domain,
                username=self._ssh_username,
                password=self._ssh_password,
                port=self._port)
        elif self._protocol == GvmProtocols.TLS:
            self._gvm_conn = TLSConnection(
                hostname=self._domain,
                port=self._port)
        # elif self._protocol == GvmProtocols.DEBUG:
        #     return
        else:
            raise RESTException(f'Invalid protocol: {self._protocol}!')
        self._gvm_session = Gmp(connection=self._gvm_conn, transform=self._transform)
        self._test_auth()
        self._gvm_session.connect()

    @property
    def _is_connected(self):
        return self._gvm_session.is_connected()

    def close(self):
        # if self._protocol == GvmProtocols.DEBUG:
        #     return
        self._gvm_session.disconnect()
        self._gvm_conn.disconnect()
        self._gvm_session = None
        self._gvm_conn = None

    def _get_assets(self, *args, **kwargs):
        asset_host = Gmp.types.AssetType.HOST
        with self._gvm_session as session:
            session.authenticate(self._username, self._password)
            return session.get_assets(asset_host, *args, **kwargs)

    def _get_scan_results(self, *args, **kwargs):
        with self._gvm_session as session:
            session.authenticate(self._username, self._password)
            return session.get_results(*args, **kwargs)

    def _paginated_get_assets(self, filter_terms=''):
        first = 1
        filter_str = f'rows=1 {filter_terms}'
        xml_data = self._get_assets(filter=filter_str)
        response = xml_data.get('get_assets_response', xml_data)
        try:
            total_count = int(response['asset_count']['#text'])
        except (KeyError, ValueError):
            logger.exception(f'Failed to get asset count from {response}!')
            raise
        remaining = min(total_count, MAX_NUMBER_OF_DEVICES)
        logger.info(f'Fetching OpenVAS info about {remaining} hosts')
        while remaining > 0:
            rows = min(DEVICE_PER_PAGE, remaining)
            filter_str = f'first={first} rows={rows} {filter_terms}'
            logger.info(f'Fetching next {rows} assets, {remaining} left.')
            try:
                response = self._get_assets(filter=filter_str)
                host_assets = response.get('asset')
                if host_assets and not isinstance(host_assets, list):
                    yield host_assets
                elif host_assets:
                    yield from host_assets
            except Exception:
                message = f'Failed to get assets no. {first} to {first+rows}. Skipping.'
                logger.exception(message)
                first += rows
            else:
                try:
                    first += int(response['asset_count']['page'])
                except (KeyError, ValueError):
                    logger.exception(f'Failed to fetch next devices from {self._domain}')
                    break
            finally:
                remaining -= rows

    # pylint: disable=too-many-nested-blocks,too-many-branches
    def _paginated_get_scan_results(self, filter_terms='', host=None):
        if host and not filter_terms:
            filter_terms = f'host={host}'
        logger.info(f'Fetching scan results with filter: {filter_terms}')
        first = 1
        filter_str = f'rows=1 {filter_terms}'
        xml_data = self._get_scan_results(filter=filter_str)
        response = xml_data.get('get_results_response', xml_data)
        try:
            total_count = int(response['result_count']['#text'])
        except (KeyError, ValueError):
            message = f'Failed to get scan results from {self._domain} '\
                      f'with filter {filter_str}'
            logger.exception(message)
            return
        remaining = min(total_count, MAX_NUMBER_OF_DEVICES)
        logger.info(f'Fetching OpenVAS info about {remaining} scan results')
        while remaining > 0:
            rows = min(DEVICE_PER_PAGE, remaining)
            filter_str = f'first={first} rows={rows} {filter_terms}'
            logger.info(f'Fetching next {rows} results, {remaining} left.')
            try:
                response = self._get_scan_results(filter=filter_str)
                results = response.get('result')
                # Make sure results are a list
                if results and not isinstance(results, list):
                    results = [results]
                # Make sure to only output results matching the host
                # This is a double-check in case the filter didn't work right
                if host is not None:
                    for result in results:
                        host_info = result.get('host')
                        if host_info and host_info.get('#text') != host:
                            continue
                        yield result
                elif results:
                    # If there's no need to double-filter, simply output the results
                    yield from results
            except Exception:
                message = f'Failed to get results no. {first} to {first + rows}. Skipping.'
                logger.exception(message)
                first += rows
            else:
                try:
                    first += int(response['result_count']['page'])
                except (KeyError, ValueError):
                    message = f'Failed to get next scan results from {self._domain} ' \
                              f'with filter {filter_str}'
                    logger.exception(message)
                    break
            finally:
                remaining -= rows

    def __debug_get_device_list(self):
        from axonius.utils.remote_file_utils import load_local_file
        assets_file = load_local_file({'file_path': self.__debug_file_assets})
        scans_file = load_local_file({'file_path': self.__debug_file_scans})
        assets = xmltodict.parse(assets_file)['get_assets_response']
        results = xmltodict.parse(scans_file)['get_results_response']
        for asset in assets.get('asset'):
            name = asset.get('name')
            asset['x_scan_results'] = list()
            for result in results.get('result'):
                host_info = result.get('host')
                if host_info and host_info.get('#text') == name:
                    asset['x_scan_results'].append(result)
            yield asset

    def get_device_list(self):
        # if self._protocol == GvmProtocols.DEBUG:
        #     yield from self.__debug_get_device_list()
        #     return
        for asset in self._paginated_get_assets():
            host_identifier = asset.get('name')
            scan_filter = f'host={host_identifier}'
            try:
                asset['x_scan_results'] = list(self._paginated_get_scan_results(
                    filter_terms=scan_filter))
            except Exception as e:
                message = f'Failed to parse scan results for {host_identifier}: {str(e)}'
                logger.exception(message)
                asset['x_scan_results'] = list()
            yield asset

    def _test_auth(self):
        with self._gvm_session as auth_test:
            result_dict = auth_test.authenticate(self._username, self._password)
            result = result_dict.get('authenticate_response', result_dict)
            if result.get('@status', None) != '200':
                message = f'Failed to authenticate! The response was: {result_dict}'
                raise RESTException(message)
