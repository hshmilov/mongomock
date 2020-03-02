import itertools
import logging

import xmltodict

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

from microfocus_sa_adapter.consts import HEADERS, DEVICE_PER_PAGE

logger = logging.getLogger(f'axonius.{__name__}')


def xml_load(obj, use_dict=True, raw=True):
    kwargs = {}

    if use_dict:
        kwargs['dict_constructor'] = dict

    if not raw:
        kwargs['attr_prefix'] = ''
        kwargs['cdata_key'] = 'text'

    try:
        return xmltodict.parse(obj, **kwargs)
    except Exception:
        msg = 'Unable to parse python object into SOAP XML'
        raise RESTException(msg)


def xml_dump(obj, pretty=True, indent='  '):
    try:
        return xmltodict.unparse(obj, pretty=pretty, indent=indent)
    except Exception:
        msg = 'Unable to parse SOAP XML to python object'
        raise RESTException(msg)


def chunker(iterable, num, fillvalue=None):
    """Chunk up iterables."""
    return itertools.zip_longest(*([iter(iterable)] * num), fillvalue=fillvalue)


def parse_bool_type(obj):
    return obj == 'true'


def parse_int_type(obj):
    try:
        return int(obj)
    except Exception:
        return obj


def parse_xsi_type(xsi_type, value):
    if xsi_type == 'xsd:boolean':
        return parse_bool_type(value)
    if xsi_type.endswith(':long'):
        return parse_int_type(value)
    return value


def parse_vo_ref(ref_raw):
    vo_ref = {'_hrefs': {}}
    for k, v in ref_raw.items():
        if not isinstance(v, dict):
            continue
        if 'text' in v and 'xsi:type' in v:
            vo_ref[k] = parse_xsi_type(xsi_type=v['xsi:type'], value=v['text'])
        elif v.get('xsi:nil', '').lower() == 'true':
            vo_ref[k] = None
        elif v.get('href', ''):
            href = v['href'].lstrip('#')
            vo_ref['_hrefs'][href] = k
    return vo_ref


class MicrofocusSaConnection(RESTConnection):
    """ rest client for MicrofocusSa adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='', headers=HEADERS, **kwargs)

    def _connect(self):
        if not self._username or not self._password:
            msg = 'No username or password'
            raise RESTException(msg)

        self.get_api_ver()

    def get_device_list(self):
        metadata = {'server_version': self.get_api_ver()}
        for device_raw in self.get_server_vos():
            yield device_raw, metadata

    def _xml_post(self, path, data):
        return self._post(
            path, body_params=data, do_basic_auth=True, use_json_in_body=False, use_json_in_response=False,
        )

    def get_server_refs(self):
        response = self._xml_post(path=self._service_server, data=self._build_xml_get_refs())
        return self._parse_refs(obj=response)

    def get_server_vos(self):
        refs = self.get_server_refs()
        for data in self._build_xml_get_vos(refs=refs):
            response = self._xml_post(path=self._service_server, data=data)
            yield from self._parse_vo_refs(obj=response)

    def get_api_ver(self):
        if not hasattr(self, '_api_version'):
            response = self._xml_post(path=self._service_console, data=self._build_xml_get_ver())
            self._api_version = self._parse_ver(obj=response)
        return self._api_version

    @property
    def _service_server(self):
        return 'osapi/com/opsware/server/ServerService'

    @property
    def _service_console(self):
        return 'osapi/com/opsware/shared/TwistConsoleService'

    @staticmethod
    def _parse_body_el(obj):
        obj = xml_load(obj=obj, raw=False)

        try:
            return obj['soapenv:Envelope']['soapenv:Body']
        except RESTException:
            msg = 'Unable to parse SOAP envelope from response'
            raise RESTException(msg)

    def _parse_vo_refs(self, obj):
        body = self._parse_body_el(obj=obj)

        refs_raw = body['multiRef']

        vo_refs = []
        href_lookups = {}

        for ref_raw in refs_raw:
            ref_type = ref_raw.get('xsi:type', '')

            if ref_type.endswith('ServerVO'):  # we're in a server vo ref
                # mid = ref_raw.get('mid', {}).get('text', '')
                vo_refs.append(parse_vo_ref(ref_raw=ref_raw))
            else:
                href_id = ref_raw['id']

                if 'text' in ref_raw:
                    href_type = ref_raw['xsi:type']
                    value = ref_raw['text']
                    href_lookups[href_id] = parse_xsi_type(xsi_type=href_type, value=value)
                elif 'name' in ref_raw:
                    href_id = href_id[0]
                    href_inner = ref_raw['name']
                    href_type = href_inner['xsi:type']
                    value = href_inner['text']
                    href_lookups[href_id] = parse_xsi_type(xsi_type=href_type, value=value)

        for vo_ref in vo_refs:
            vo_hrefs = vo_ref.pop('_hrefs')
            vo_ref.update({v: href_lookups[k] for k, v in vo_hrefs.items() if k in href_lookups})
            yield vo_ref

    def _parse_refs(self, obj):
        body = self._parse_body_el(obj=obj)

        refs_raw = body['multiRef']
        href_lookups = {}
        ref_lookups = []

        for ref_raw in refs_raw:
            ref_id_long = ref_raw.get('idAsLong', {}).get('href', '').lstrip('#')

            if ref_id_long:  # it's an asset ref
                try:
                    ref_lookups.append(ref_raw['id'][1]['href'].lstrip('#'))
                except Exception:
                    msg = f'Problem getting [id][1][href] from supposed asset raw_ref {ref_raw}'
                    logger.exception(msg)
                    continue
            else:  # it's a lookup ref
                try:
                    ref_id = ref_raw['id']
                    ref_text = ref_raw['text']
                except Exception:
                    msg = f'Problem getting [id] or [text] from supposed href raw_ref {ref_raw}'
                    logger.exception(msg)
                    continue

                href_lookups[ref_id] = ref_text

        return sorted([y for y in [href_lookups.get(x) for x in ref_lookups] if y])

    def _parse_ver(self, obj):
        body = self._parse_body_el(obj=obj)
        return body['ns1:getAPIVersionLabelResponse']['getAPIVersionLabelReturn']['text']

    @property
    def _filter_expr(self):
        return None

    @property
    def _namespace(self):
        return {'@xmlns:ns0': 'http://shared.opsware.com'}

    @staticmethod
    def _build_xml_body(body_tree):
        soap_env = {'@xmlns:soap-env': 'http://schemas.xmlsoap.org/soap/envelope/'}
        soap_env['soap-env:Body'] = body_tree
        env = {'soap-env:Envelope': soap_env}
        return xml_dump(env)

    def _build_xml_get_ver(self):
        body_tree = {'ns0:getAPIVersionLabel': self._namespace}
        return self._build_xml_body(body_tree=body_tree)

    def _build_xml_get_refs(self):
        namespace = self._namespace
        namespace['filter'] = {'expression': self._filter_expr}
        body_tree = {'ns0:findServerRefs': namespace}
        return self._build_xml_body(body_tree=body_tree)

    def _build_xml_get_vos(self, refs):
        for chunk in chunker(iterable=refs, num=DEVICE_PER_PAGE, fillvalue=None):
            server_refs = [{'id': x} for x in chunk if x is not None]
            namespace = self._namespace
            namespace['selves'] = {'ServerRef': server_refs}
            body_tree = {'ns0:getServerVOs': namespace}
            yield self._build_xml_body(body_tree=body_tree)
