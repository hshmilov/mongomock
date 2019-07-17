import itertools
import io
import xml.etree.ElementTree as ET

import logging

logger = logging.getLogger(f'axonius.{__name__}')


def parse_xml_from_string(xml_string):
    try:
        return ET.fromstring(xml_string.replace(b'\x00', b''))
    except ET.ParseError as err:
        lineno, column = err.position
        start = lineno - 10 if lineno > 10 else 0
        lines = str(list(itertools.islice(io.StringIO(xml_string.decode('utf-8')), start, start + 10)))
        caret = '{:=>{}}'.format('^', column)
        msg = '{}\n{}\n{}'.format(err, lines, caret)
        logger.exception(f'Exception while parsing xml: {msg}')
        raise
