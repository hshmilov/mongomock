"""
Many helper functions to wrap impacket's com handling
"""
from impacket.dcerpc.v5.dcom.oaut import IID_IDispatch, string_to_bin, IDispatch, DISPPARAMS, DISPATCH_PROPERTYGET, \
    VARIANT, VARENUM, DISPATCH_METHOD, DISPATCH_PROPERTYPUT
from impacket.dcerpc.v5.dtypes import NULL
import com_interfaces.idispatch


def new_idispatch_from_clsid(dcom, clsid):
    """
    Creates a new IDispatch interface from a clsid string.
    :param DCOMConnection dcom: a DCOMConnection object.
    :param str clsid: a string representing the class id.
    :return: a new com_interfaces.idispatch.IDispatch interface (Axonius wrapper of IDispatch)
    """

    return com_interfaces.idispatch.IDispatch(IDispatch(dcom.CoCreateInstanceEx(string_to_bin(clsid), IID_IDispatch)))
