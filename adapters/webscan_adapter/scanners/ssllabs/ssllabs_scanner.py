import logging

from typing import List

from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass
from webscan_adapter.scanners.service_scanner import ServiceScanner
from webscan_adapter.scanners.ssllabs import ssllabs

logger = logging.getLogger(f'axonius.{__name__}')


class Protocol(SmartJsonClass):
    _id = Field(int, 'Id')
    name = Field(str, 'Name')
    version = Field(str, 'Version')


class Suite(SmartJsonClass):
    _id = Field(int, 'Id')
    name = Field(str, 'Name')
    cipher_strength = Field(int, 'Cipher Strength')
    kx_type = Field(str, 'KX Type')
    kx_strength = Field(int, 'KX Strength')
    named_group_name = Field(str, 'Named Group Name')


class Suites(SmartJsonClass):
    protocol_id = Field(int, 'Protocol Id')
    lst = ListField(Suite, 'List')


class EndpointDetails(SmartJsonClass):
    protocols = ListField(Protocol, 'Protocols')
    suites = ListField(Suites, 'Suites')
    server_signature = Field(str, 'Server Signature')
    prefix_delegation = Field(bool, 'Prefix Delegation')
    npn_protocols = Field(str, 'NPN Protocols')
    alpn_protocols = Field(str, 'ALPN Protocols')
    heartbleed = Field(bool, 'Heartbleed')
    heartbeat = Field(bool, 'Heartbeat')
    poodle = Field(bool, 'Poodle')
    drown_errors = Field(bool, 'Drown Errors')
    drown_vulnerable = Field(bool, 'Drown Vulnerable')


class Endpoint(SmartJsonClass):
    ip_address = Field(str, 'IP Address')
    server_name = Field(str, 'Server Name')
    grade = Field(str, 'Grade')
    has_warnings = Field(bool, 'Has Warnings')
    is_exceptional = Field(bool, 'Is Exceptional')
    details = Field(EndpointDetails, 'Details')


class SSLLabs(SmartJsonClass):
    host = Field(str, 'Host')
    protocol = Field(str, 'Protocol')
    endpoints = ListField(Endpoint, 'Endpoints')


class SSLLabsScanner(ServiceScanner):
    """
    Get SSL Certificate data
    """

    @staticmethod
    def get_ssllabs_data(host: str, proxy=None):
        """
        Get cert data from ssllabs
        :param url: url to get the cert from
        :return: dict of cert data
        """
        logger.debug(f'Getting {host} ssllabs info')
        assessment = ssllabs.SSLLabsAssessment(host=host, proxy=proxy)
        info = assessment.analyze()
        return info

    def scan(self):
        """
        Get cert data form the given url / domain
        :return: cert data results
        """
        self.results = self.get_ssllabs_data(self.domain or self.url, proxy=self.https_proxy)
        return self.results

    @staticmethod
    def get_protocols(protocols_data: dict) -> List[Protocol]:
        protocols_lst = []
        for protocol in protocols_data:
            prot_obj = Protocol(_id=protocol.get('id'),
                                name=protocol.get('name'),
                                version=protocol.get('version'))
            protocols_lst.append(prot_obj)
        return protocols_lst

    @staticmethod
    def get_suites(suites_data: dict) -> List[Suites]:
        suites_obj_lst = []
        for suite in suites_data:
            suite_obj_lst = []
            suite_lst = suite.get('list', {}) or {}
            for suite_item in suite_lst:
                suite_obj = Suite(_id=suite_item.get('id'),
                                  name=suite_item.get('name'),
                                  cipher_strength=suite_item.get('cipherStrength'),
                                  kx_type=suite_item.get('kxType'),
                                  kx_strength=suite_item.get('kxStrength'),
                                  named_group_name=suite_item.get('namedGroupName')
                                  )
                suite_obj_lst.append(suite_obj)
            suites_obj_lst.append(Suites(protocol_id=suite.get('protocol'),
                                         lst=suite_obj_lst))
        return suites_obj_lst

    @staticmethod
    def get_endpoints_details(endpoint_details) -> EndpointDetails:
        endpoint_details_obj = EndpointDetails(
            protocols=SSLLabsScanner.get_protocols(endpoint_details.get('protocols', []) or []),
            suites=SSLLabsScanner.get_suites(endpoint_details.get('suites', []) or []),
            server_signature=endpoint_details.get('serverSignature'),
            prefix_delegation=endpoint_details.get('prefixDelegation'),
            npn_protocols=endpoint_details.get('npnProtocols'),
            alpn_protocols=endpoint_details.get('alpnProtocols'),
            heartbleed=endpoint_details.get('heartbleed'),
            heartbeat=endpoint_details.get('heartbeat'),
            poodle=endpoint_details.get('poodle'),
            drown_errors=endpoint_details.get('drownErrors'),
            drown_vulnerable=endpoint_details.get('drownVulnerable')
        )
        return endpoint_details_obj

    def parse(self, device: DeviceAdapter):
        """
        Parse the scan results into a DeviceAdapter data
        :param device: DeviceAdapter to add the results
        :return: None
        """
        if not self.results:
            return
        data = self.results
        endpoint_obj_lst = []
        for endpoint in data.get('endpoints', []):
            endpoint_obj = Endpoint(ip_address=endpoint.get('ipAddress'),
                                    server_name=endpoint.get('serverName'),
                                    grade=endpoint.get('grade'),
                                    has_warnings=endpoint.get('hasWarnings'),
                                    is_exceptional=endpoint.get('isExceptional'),
                                    details=self.get_endpoints_details(endpoint.get('details', {}) or {}))

            endpoint_obj_lst.append(endpoint_obj)

        ssllabs_data = SSLLabs(host=data.get('host'),
                               protocol=data.get('protocol'),
                               endpoints=endpoint_obj_lst)
        device.ssllabs = ssllabs_data
