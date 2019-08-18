""" utils for juniper xml parsing """

from xml.etree import ElementTree

import lxml.etree


# pylint: disable=protected-access
def cast_to_xml_if_needed(xml):
    """ cast argument to xml if it is string
        if we got lxml element, convert to xml"""
    if isinstance(xml, (lxml.etree._Element, lxml.etree._ElementTree)):
        xml = lxml.etree.tostring(xml, xml_declaration=True)
    if isinstance(xml, (str, bytes)):
        xml = ElementTree.fromstring(xml)
    return xml


def strip_rpc_if_needed(xml):
    """
        sometimes juniper xml returns with rpc-reply header, sometimes not.
        strip the header if needed.
    """
    if gettag(xml.tag) == 'rpc-reply':
        xml = xml[0]
    return xml


def prepare(xml):
    """ call all pre parsing functions """
    xml = cast_to_xml_if_needed(xml)
    xml = strip_rpc_if_needed(xml)
    return xml


def gettext(text: str):
    """ for some reason, somtimes we get string from xml with \n in start and end.
        strip t  - We should investiage more """

    if not text:
        return text

    if text[0] == '\n' and text[-1] == '\n':
        text = text[1:-1]

    return str(text)


def gettag(tag: str):
    """ sometimes junos tag return with {<version>} prefix,
        remote it if possible """
    if not tag:
        return tag
    if tag[0] == '{' and '}' in tag:
        tag = tag[tag.index('}') + 1:]

    return str(tag)
