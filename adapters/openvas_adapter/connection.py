import datetime
import logging
from collections import defaultdict

import xmltodict

from urllib3.util.url import parse_url
# pylint: disable=import-error
from gvm.protocols.latest import Gmp
from gvm.connections import TLSConnection, SSHConnection
from openvas_adapter.consts import GvmProtocols, MAX_NUMBER_OF_DEVICES, DEVICE_PER_PAGE, FILTER_DATE_FORMAT
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
                 timedelta: datetime.timedelta = None,
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
        self._timedelta = timedelta

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
            total_count = int(response['asset_count']['filtered'])  # the "#text" attribute is a complete total!
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
                    host_assets = [host_assets]
                if not host_assets:
                    logger.info(f'Done paginating hosts')
                    break
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
    def _paginated_get_scan_results(self):
        """
        Paginate scan results with filter: severity>0 AND created>(now - last_seen_timedelta)
        :return: iterable of scan results [dict, dict, ...]
        """
        # Build filters
        timedelta = self._timedelta or datetime.timedelta(days=90)
        filter_datetime = datetime.datetime.now() - timedelta
        filter_datetime_str = filter_datetime.strftime(FILTER_DATE_FORMAT)
        filter_terms = f'severity>0 and created>{filter_datetime_str}'

        filter_str = f'rows=1 {filter_terms}'
        logger.info(f'Fetching scan results with filter: {filter_terms}')

        # get a count of expected results
        xml_data = self._get_scan_results(filter=filter_str)
        response = xml_data.get('get_results_response', xml_data)
        try:
            total_count = int(response['result_count']['filtered'])  # The "#text" attribute is a TOTAL OF ALL EVER!
        except (KeyError, ValueError):
            message = f'Failed to get scan results from {self._domain} '\
                      f'with filter {filter_str}'
            logger.exception(message)
            return
        # Get actual results
        first = 1
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
                if not results:
                    logger.info(f'Done paginating scans')
                    break
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

    def _get_scans_dict(self):
        """
        Get a dictionary keyed by host identifier with lists of scan results
        Scan results are filtered by date and severity>0
        See _paginated_get_scan_results() for exact filter conditions
        :return: dict{host_str: [scan_dict, scan_dict, ...] }
        """
        result_dict = defaultdict(list)
        for scan in self._paginated_get_scan_results():
            try:
                if not isinstance(scan, dict):
                    logger.warning(f'Bad scan result. Expected dict, got {type(scan)} instead.')
                    logger.debug(f'Bad scan result is: {scan}')
                    continue
                host_info = scan.get('host')
                if isinstance(host_info, dict) and host_info.get('#text'):
                    host = host_info.get('#text')
                    result_dict[host].append(scan)
                else:
                    logger.warning(f'Invalid host info: {host_info}')
                    continue
            except Exception as e:
                logger.warning(f'Error parsing scan result: got {str(e)}')
                logger.debug(f'Error parsing scan result {scan}')
        return result_dict

    def get_device_list(self):
        try:
            scan_results = self._get_scans_dict()
        except Exception:
            logger.exception(f'Failed to get scan results.')
            scan_results = {}

        for asset in self._paginated_get_assets():
            if not isinstance(asset, dict):
                logger.warning(f'Failed to yield asset. Expected dict, got {type(asset)} instead.')
                logger.debug(f'Failed asset is: {asset}')
                continue
            host_identifier = asset.get('name')
            try:
                asset['x_scan_results'] = scan_results.get(host_identifier)
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
