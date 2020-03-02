import datetime
import logging

from axonius.utils.datetime import parse_date

from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass

logger = logging.getLogger(f'axonius.{__name__}')


def parse_owner(owner_dict):
    if owner_dict and isinstance(owner_dict, dict):
        return owner_dict.get('name')
    return None


class OpenvasSourceDetail(SmartJsonClass):
    id = Field(str, 'Source ID')
    src_type = Field(str, 'Source Type')
    # data = Field(str, 'Source Data')
    # name = Field(str, 'Name')
    # deleted = Field(bool, 'Deleted')


class OpenvasHostDetails(SmartJsonClass):
    name = Field(str, 'Source name')
    source = Field(OpenvasSourceDetail, 'Source Details')
    value = Field(str, 'Value')

    @classmethod
    def from_dict(cls, detail):
        host_src = detail.get('source')
        if host_src and isinstance(host_src, dict):
            src_detail = OpenvasSourceDetail(
                id=host_src.get('@id'),
                src_type=host_src.get('type')
            )
        else:
            src_detail = None
        return cls(
            name=detail.get('name'),
            source=src_detail,
            value=detail.get('value')
        )


class HostAssetIdentifier(SmartJsonClass):
    id = Field(str, 'ID')
    created = Field(datetime.datetime, 'Creation Time')
    mod_time = Field(datetime.datetime, 'Modification Time')
    name = Field(str, 'Name')
    # source = Field(OpenvasSourceDetail, 'Source')
    value = Field(str, 'Value')

    @classmethod
    def from_dict(cls, ident_dict):
        return cls(
            id=ident_dict.get('@id'),
            created=parse_date(ident_dict.get('creation_time')),
            mod_time=parse_date(ident_dict.get('modified_time')),
            name=ident_dict.get('name'),
            value=ident_dict.get('value')
        )


class ScanPort(SmartJsonClass):
    value = Field(int, 'Port Number')
    proto = Field(str, 'Protocol')
    name = Field(str, 'Port Name')

    @staticmethod
    def from_dict(port_str):
        if not port_str or not isinstance(port_str, str):
            return None
        try:
            val, proto = port_str.split('/')
        except Exception as e:
            message = f'Failed to parse scan port from {port_str}: {str(e)}'
            logger.warning(message)
            return None
        try:
            return ScanPort(
                proto=proto,
                value=int(val)
            )
        except ValueError:
            return ScanPort(
                proto=proto,
                name=val
            )


class ScanQOD(SmartJsonClass):
    qod_type = Field(str, 'Detection Type')
    qod_value = Field(int, 'Value')

    @staticmethod
    def from_dict(qod_dict):
        if not qod_dict or not isinstance(qod_dict, dict):
            return None
        try:
            return ScanQOD(
                qod_type=qod_dict.get('type'),
                qod_value=int(qod_dict.get('value'))
            )
        except Exception as e:
            message = f'Failed to parse QOD data from {qod_dict}: {str(e)}'
            logger.warning(message)
            return None


class NvtInfo(SmartJsonClass):
    oid = Field(str, 'OID')
    bid = Field(str, 'BID')
    cve = Field(str, 'CVE ID')
    cvss_base = Field(float, 'CVSS Base')
    family = Field(str, 'Scan Family')
    name = Field(str, 'Name')
    nvt_type = Field(str, 'Type')
    xref = ListField(str, 'X-Ref')

    @staticmethod
    def from_dict(nvt_dict):
        if not nvt_dict or not isinstance(nvt_dict, dict):
            return None
        xref_raw = nvt_dict.get('xref')
        xref = None
        if isinstance(xref_raw, str) and xref_raw.upper() != 'NOXREF':
            xref = xref_raw.split(', ') or None
        # remove tags from result, so it won't clog up the json
        nvt_dict.pop('tags', None)
        try:
            cvss_base = float(nvt_dict.get('cvss_base', '0.0'))
        except Exception:
            cvss_base = None
        return NvtInfo(
            oid=nvt_dict.get('@oid'),
            bid=nvt_dict.get('bid'),
            cve=nvt_dict.get('cve'),
            cvss_base=cvss_base,
            family=nvt_dict.get('family'),
            name=nvt_dict.get('name'),
            nvt_type=nvt_dict.get('type'),
            xref=xref
        )


class OpenvasScanResult(SmartJsonClass):
    id = Field(str, 'Scan ID')
    comment = Field(str, 'Comment')
    descr = Field(str, 'Description')
    created = Field(datetime.datetime, 'Creation Time')
    mod_time = Field(datetime.datetime, 'Modification Time')
    name = Field(str, 'Name')
    port = Field(ScanPort, 'Port')
    qod = Field(ScanQOD, 'Quality of Detection')
    nvt_ver = Field(datetime.datetime, 'Scan NVT Version')
    severity = Field(float, 'Severity')
    threat = Field(str, 'Threat Level')
    owner = Field(str, 'Scan Owner')
    orig_sev = Field(float, 'Original Severity')
    orig_threat = Field(str, 'Original Threat Level')
    nvt = Field(NvtInfo, 'NVT Info')

    @staticmethod
    def from_dict(scan_dict):
        if not scan_dict:
            return None
        _id = scan_dict['@id']  # fail here if no id, this is intentional
        scan_dict.pop('host', None)  # Remove redundant host info
        mod_time = parse_date(scan_dict.get('modification_time'))
        created = parse_date(scan_dict.get('creation_time'))
        nvt_ver = parse_date(scan_dict.get('scan_nvt_version'))
        qod = ScanQOD.from_dict(scan_dict.get('qod'))
        nvt = NvtInfo.from_dict(scan_dict.get('nvt'))
        port = ScanPort.from_dict(scan_dict.get('port'))
        try:
            sev = float(scan_dict.get('severity', '0.0'))
        except BaseException:
            sev = None
        try:
            orig_sev = float(scan_dict.get('original_severity', '0.0'))
        except BaseException:
            orig_sev = None
        return OpenvasScanResult(
            id=_id,
            comment=scan_dict.get('comment'),
            descr=scan_dict.get('description'),
            mod_time=mod_time,
            created=created,
            name=scan_dict.get('name'),
            port=port,
            qod=qod,
            nvt_ver=nvt_ver,
            severity=sev,
            threat=scan_dict.get('threat'),
            owner=parse_owner(scan_dict.get('owner')),
            orig_sev=orig_sev,
            orig_threat=scan_dict.get('original_threat'),
            nvt=nvt,
        )
