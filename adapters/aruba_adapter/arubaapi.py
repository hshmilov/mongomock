"""Library for retrieving semi-formatted CLI command output from ArubaOS"""

import logging
import time
import xml.etree.ElementTree as ET
from urllib.parse import quote as urlquote

import requests

logger = logging.getLogger(f'axonius.{__name__}')


class ArubaAPI:
    """Performs CLI commands over the ArubaOS HTTPS API"""

    _SESSION_COOKIE = 'SESSION'

    def __init__(self, device, username, password, port=4343, insecure=False):
        """Instantiates an ArubaAPI object

        :param device: Name or IP address of controller
        :type device: str
        :param username: Username to log in with
        :type username: str
        :param password: Password to log in with
        :type password: str
        :param port: Port running HTTPS server
        :type port: int
        :default port: 4343
        :param insecure: Disables verification of the TLS certificate
        :type insecure: bool
        :default insecure: False
        """
        if device.startswith('https://'):
            device = device[len('https://'):]
        self.device = device
        self.port = port
        self.username = username
        self.password = password
        self.verify = not insecure
        self.session = requests.Session()
        if not self.verify:
            try:
                from requests.packages.urllib3.exceptions import InsecureRequestWarning
                requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
            except ImportError:
                pass

    def __enter__(self):
        self._login()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def _uri(self):
        uri = 'https://{}'.format(self.device)
        if self.port:
            uri = '{}:{}'.format(uri, self.port)
        return uri

    def _login(self):
        form_data = {
            'opcode': 'login',
            'url': '/',
            'needxml': 0,
            'uid': self.username,
            'passwd': self.password
        }
        resp = self.session.post('{}/screens/wms/wms.login'.format(self._uri()),
                                 data=form_data, verify=self.verify, timeout=(5, 30))
        logger.debug('Login: status %s; cookies %s', resp.status_code, resp.cookies)
        logger.info('logged in to %s', self.device)

    def _logout(self):
        resp = self.session.get('{}/logout.html'.format(self._uri()), verify=self.verify, timeout=(5, 30))
        # For some reason it's always a 404 when logging out
        if resp.status_code != 404:
            logger.error('Unexpected status code %s while logging out', resp.status_code)
        self.session = requests.Session()
        logger.info('logged out of %s', self.device)

    @staticmethod
    def _ms_time():
        return int(time.time() * 1000)

    def _cli_param(self, command):
        """Returns URL parameters AOS requires for running commands

        :param command: Command to run
        :type command: str
        :returns: URL-encoded parameter string
        """
        return '{}@@{}&UIDARUBA={}'.format(urlquote(command), self._ms_time(),
                                           self.session.cookies[self._SESSION_COOKIE]).encode()

    def cli(self, command, debug=False):
        """Performs CLI command on ArubaOS device

        :param command: Command to run
        :type command: str
        :returns: dict
        """
        resp = self.session.get('{}/screens/cmnutil/execCommandReturnResult.xml'.format(self._uri()),
                                params=self._cli_param(command), verify=self.verify, timeout=(5, 30))
        if resp.status_code != 200:
            raise ValueError('Bad status code {}: {}'.format(resp.status_code, resp.text))
        try:
            logger.debug('Got text %r', resp.text)
            if resp.text:
                xdata = ET.fromstring(resp.text)
                logger.debug('Successfully parsed %d bytes', len(resp.text))
            else:
                logger.info('No data received for %r', command)
                return None
        except ET.ParseError:
            raise Exception('XML Parsing error')
        if not debug:
            return self.parse_xml(xdata)
        return self.parse_xml(xdata), resp.text

    def close(self):
        """Logs out of the controller"""
        self._logout()

    @staticmethod
    def _hacky_table(table_name):
        """Checks for tables which have no headers and should be named data"""
        return table_name in ['Power Status']

    @staticmethod
    def _parse_hacky_xml_table(xmldata):
        """Parses tables which should actually be named data"""
        data = dict()
        name = xmldata.attrib.get('tn')
        rows = [[x.text for x in y] for y in xmldata.findall('r')]
        for row in rows:
            data[row[0]] = row[1]
        return {name: data}

    @staticmethod
    def _parse_xml_table(xmldata):
        table = []
        name = xmldata.attrib.get('tn')

        rows = [[x.text for x in y] for y in xmldata.findall('r')]
        if ArubaAPI._hacky_table(name):
            rows = list(zip(*rows))

        th = xmldata.find('th')
        if th:
            header = [x.text for x in th.findall('h')]
        else:
            header = rows[0]
            rows = rows[1:]
        for row in rows:
            table.append(dict(zip(header, row)))
        return {name: table}

    @staticmethod
    def parse_xml(xmldata):
        """Parses ArubaOS XML

        :param xmldata: XML response
        :type xmldata: xml.etree.ElementTree
        """
        ret = {'data': []}
        for elem in xmldata:
            try:
                if elem.tag == 'data':
                    if not elem.text:
                        # Skip null data
                        continue
                    if elem.attrib.get('name'):
                        # Named data
                        name = elem.attrib.get('name')
                        if name in ret:
                            ret[name].append(elem.text)
                        else:
                            ret[name] = [elem.text]
                    else:
                        # Anonymous data
                        ret['data'].append(elem.text)
                elif elem.tag == 't':
                    ret.update(ArubaAPI._parse_xml_table(elem))
                else:
                    raise ValueError('Unknown tag {} {}'.format(elem.tag, elem.text))
            except Exception:
                logger.exception(f'Problem with xml elem {str(elem)}')
        return ret
