"""
A generic IDispatch interface, to make it easy to implement com interfaces
"""
from impacket.dcerpc.v5.dcom.oaut import DISPPARAMS, VARIANT, VARENUM, DISPATCH_PROPERTYGET, DISPATCH_PROPERTYPUT, \
    DISPATCH_METHOD, FUNCKIND, INVOKEKIND, IID_IDispatch, string_to_bin
from impacket.dcerpc.v5.dcom.oaut import IDispatch as OAUT_IDispatch
from impacket.dcerpc.v5.dcomrt import OBJREF, FLAGS_OBJREF_CUSTOM, OBJREF_CUSTOM, OBJREF_HANDLER, \
    OBJREF_EXTENDED, OBJREF_STANDARD, FLAGS_OBJREF_HANDLER, FLAGS_OBJREF_STANDARD, FLAGS_OBJREF_EXTENDED, \
    IRemUnknown2, INTERFACE
from impacket.dcerpc.v5.dtypes import NULL
import datetime

DISPID_PROPERTYPUT = 0xFFFFFFFD  # I can see in C sources this is -3, but for some reason impacket wants it as unsigned
# so this is how it works (might be a bug in impacket..)
LCID_EN_US = 0x403

# 30. December 1899, midnight.  For VT_DATE.
_com_null_date = datetime.datetime(1899, 12, 30, 0, 0, 0)


class IDispatch(object):
    """
    An IDispatch COM interface.
    Allows you to get, put and call members and methods simply by accessing them.
    """

    def __init__(self, oaut_idispatch):
        """
        Initializes an IDispatch class.
        :param oaut_idispatch: an impacket.dcerpc.v5.dcom.oaut.IDispatch object
        """

        self.interface = oaut_idispatch
        self.name_to_id = dict()            # name to id translation for Invoke
        self.propertyget_dict = dict()      # a dict representing all properties we can get
        self.propertyput_dict = dict()      # a dict representing all properties we can put
        self.propertyputref_dict = dict()   # a dict representing all the propertys we can put with ref. not used by us
        self.method_dict = dict()           # a dict representing all methods we can call
        self.__parse_type_info()

    def __parse_type_info(self):
        """
        Tries to understand all methods and properties of this type.
        :return:
        """
        # This whole code is currently disabled, since it takes way too much time.
        # TODO: fix timing
        # TODO more: cache results for the same interfaces. We have the same interfaces again and again
        return
        """
        assert self.interface.GetTypeInfoCount()['pctinfo'] != 0, "No type information for interface"
        i_type_info = self.interface.GetTypeInfo()
        i_type_attr = i_type_info.GetTypeAttr()
        for x in range(i_type_attr['ppTypeAttr']['cFuncs']):
            func_desc = i_type_info.GetFuncDesc(x)
            names = i_type_info.GetNames(func_desc['ppFuncDesc']['memid'], 255)
            if names['pcNames'] > 0 and func_desc['ppFuncDesc']['funckind'] == FUNCKIND.FUNC_DISPATCH:
                name = names['rgBstrNames'][0]['asData']

                # Parse parameter types
                param_types = []
                for p in func_desc['ppFuncDesc']['lprgelemdescParam']:
                    param_types.append(p['tdesc']['vt'])

                # Parse invoke kind
                invoke_kind = func_desc['ppFuncDesc']['invkind']
                if invoke_kind == INVOKEKIND.INVOKE_PROPERTYGET:
                    self.propertyget_dict[name] = param_types
                elif invoke_kind == INVOKEKIND.INVOKE_PROPERTYPUT:
                    self.propertyput_dict[name] = param_types
                elif invoke_kind == INVOKEKIND.INVOKE_PROPERTYPUTREF:
                    self.propertyputref_dict[name] = param_types
                elif invoke_kind == INVOKEKIND.INVOKE_FUNC:
                    self.method_dict[name] = param_types
        """

    def __get_id_from_name(self, name):
        """
        Uses the interface and gets the ID from a property/method name.
        Caches the result.
        :param name: the name of the property/method
        :return: the
        """

        # IDispatch has a GetIdsOfNames method that allows us to get an ID of a method/property, this is what
        # we need to pass to Invoke (an IDispatch method).
        if name not in self.name_to_id:
            self.name_to_id[name] = self.interface.GetIDsOfNames((name,))[0]

        return self.name_to_id[name]

    def __new_idispatch_from_interface_response(self, interface, resp):
        """
        If some interface has a method that returns new interface, use this function to get an IDispatch interface of it.
        :param interface: an impacket.dcerpc.v5.dcom.oaut.IDispatch interface
        :param resp: a response from an Invoke call that was made on the interface
        :return:
        """

        # This whole code was taken from https://github.com/CoreSecurity/impacket/blob/master/examples/dcomexec.py
        objRefType = OBJREF(''.join(resp))['flags']
        objRef = None

        if objRefType == FLAGS_OBJREF_CUSTOM:
            objRef = OBJREF_CUSTOM(''.join(resp))
        elif objRefType == FLAGS_OBJREF_HANDLER:
            objRef = OBJREF_HANDLER(''.join(resp))
        elif objRefType == FLAGS_OBJREF_STANDARD:
            objRef = OBJREF_STANDARD(''.join(resp))
        elif objRefType == FLAGS_OBJREF_EXTENDED:
            objRef = OBJREF_EXTENDED(''.join(resp))
        else:
            raise ValueError("Unknown OBJREF Type! 0x%x" % objRefType)

        return IDispatch(
            OAUT_IDispatch(
                IRemUnknown2(
                    INTERFACE(
                        interface.get_cinstance(), None, interface.get_ipidRemUnknown(), objRef['std']['ipid'],
                        oxid=objRef['std']['oxid'], oid=objRef['std']['oxid'], target=interface.get_target())
                )
            )
        )

    def __parse_variant(self, var_union):
        """
        gets a _varUnion result and returns the pythonic object representing it.
        :param var_union: an object of type impacket.dcerpc.v5.dcom.oaut.varUnion
        :return:
        """
        # Only some types are supported. For more information, please see the comments in __create_disp_params.
        assert len(var_union.structure) == 1, "Structure of response is not 1: {0}".format(var_union.structure)
        field = var_union.structure[0][0]
        val = var_union[field]

        if field == 'boolVal':
            # Boolean
            return bool(val)
        elif field in ['lVal', 'iVal', 'ulVal', 'uiVal', 'intVal', 'uintVal']:
            # Some kind of an integer
            return int(val)
        elif field == 'pdispVal':
            # A new interface
            return self.__new_idispatch_from_interface_response(self.interface, val['abData'])
        elif field == 'bstrVal':
            # A string. Sometimes returns just as a string and sometimes as another object
            if type(val) == str:
                return val
            else:
                # This Should be impacket.dcerpc.v5.dcom.oaut.FLAGGED_WORD_BLOB
                # But if its not, then we don't know how to parse it, we better have an exception here.
                # This will throw an exception if its not the desired type, since 'asData' is what we expect
                # in a string.
                return val['asData']
        elif field == 'date':
            # Its a date. More info here: https://msdn.microsoft.com/en-us/library/82ab7w69.aspx
            return datetime.timedelta(days=val) + _com_null_date
        elif field == 'empty':
            # None
            return None
        else:
            raise ValueError("unknown type {0} of varunion. struct is : {1}".format(field, var_union.structure))

    def __create_disp_params(self, args, args_structure, is_propertyput=None):
        """
        Create a DISPPARAMS object.
        :param args: a list of args
        :param args_structure: a list of VARENUM types
        :param bool is_propertyput: should be True is this is a list for propertyput
        :return:
        """
        disp_params = DISPPARAMS(None, False)

        if is_propertyput is True:
            # According to IDispatch::Invoke we have to put the following here.
            # https://msdn.microsoft.com/en-us/library/windows/desktop/ms221479(v=vs.85).aspx
            disp_params['cNamedArgs'] = 1
            disp_params['rgdispidNamedArgs'] = [DISPID_PROPERTYPUT]  # ???
        else:
            disp_params['cNamedArgs'] = 0
            disp_params['rgdispidNamedArgs'] = NULL

        if len(args) == 0:
            disp_params['rgvarg'] = NULL
            disp_params['cArgs'] = 0
        else:
            disp_params['cArgs'] = len(args)
            for i, arg in enumerate(args):
                # Disabled because args_structure is currently not working well.
                # varg_type = args_structure[i]

                # Avidor:
                # We only support some format (impacket unfortunately does not implement it).
                # for more information on how to extend it when we need the support, please use
                # 1. https://en.wikipedia.org/wiki/Variant_type
                # 2. http://www.quickmacros.com/help/Tables/IDP_VARIANT.html
                # 3. https://github.com/CoreSecurity/impacket/blob/master/impacket/dcerpc/v5/dcom/oaut.py (VARENUM def)
                #
                # And, the best source - where we can actual copy examples, is
                # 4. https://github.com/enthought/comtypes/blob/master/comtypes/automation.py
                #
                # args_structure is an ordered list of the types of the arguments. we should get it from the description
                # of the interface.

                varg = VARIANT(None, False)
                # Have no idea why its 5, but it always it. I thing its the size of a VARIANT struct.
                varg['clSize'] = 5

                # if varg_type == VARENUM.VT_BSTR:
                if type(arg) == str:
                    varg['vt'] = VARENUM.VT_BSTR
                    varg['_varUnion']['tag'] = VARENUM.VT_BSTR
                    varg['_varUnion']['bstrVal']['asData'] = arg

                # elif varg_type == VARENUM.VT_BOOL:
                elif type(arg) == bool:
                    assert type(arg) == bool
                    varg['vt'] = VARENUM.VT_BOOL
                    varg['_varUnion']['tag'] = VARENUM.VT_BOOL
                    # specs for VT_BOOL: https://msdn.microsoft.com/en-us/library/cc237864.aspx
                    varg['_varUnion']['boolVal'] = 0 if arg is False else 0xFFFF

                # elif varg_type == VARENUM.VT_I4 or varg_type == VARENUM.VT_USERDEFINED:
                elif type(arg) == int:
                    # Should override the VT_USERDEFINED in the vt and tag
                    varg['vt'] = VARENUM.VT_I4
                    varg['_varUnion']['tag'] = VARENUM.VT_I4
                    varg['_varUnion']['lVal'] = arg

                else:
                    raise ValueError(
                        "Type {0} not supported. please extend the create_disp_params function".format(type(arg)))

                disp_params['rgvarg'].append(varg)

        return disp_params

    def __invoke(self, dispatch_type, name, args):
        """
        Generically calls IDispatch::Invoke.
        :param int dispatch_type: DISPATCH_PROPERTYGET, DISPATCH_PROPERTYPUT, or DISPATCH_METHOD.
        :param list name: the name of the dispatch (property, method name etc)
        :param list args: a list of arguments for the property/method.
        :return:
        """
        args_structure = None
        """
        if dispatch_type == DISPATCH_PROPERTYGET:
            args_structure = self.propertyget_dict[name]
        elif dispatch_type == DISPATCH_PROPERTYPUT:
            args_structure = self.propertyput_dict[name]
        elif dispatch_type == DISPATCH_METHOD:
            args_structure = self.method_dict[name]
        else:
            raise ValueError("Unknown dispatch type {0}".format(dispatch_type))
        """

        disp_params = self.__create_disp_params(args,
                                                args_structure,
                                                is_propertyput=(dispatch_type == DISPATCH_PROPERTYPUT))

        rv = self.interface.Invoke(self.__get_id_from_name(name), LCID_EN_US, dispatch_type, disp_params, 0, [], [])

        return self.__parse_variant(rv['pVarResult']['_varUnion'])

    def get(self, property_name, optional_args=[]):
        """
        Gets a property
        :param str property_name: the name of the property
        :param list optional_args: an optional list of args
        :return: the value of the property
        """
        return self.__invoke(DISPATCH_PROPERTYGET, property_name, optional_args)

    def put(self, property_name, property_value, hard_check=False):
        """
        Sets a property
        :param str property_name: the name of the property
        :param property_value: the value of the property
        :param bool hard_check: Optional param, that, if True, gets the value after the put operation and validates
        the result is indeed what we asked for.
        :return:
        """
        res = self.__invoke(DISPATCH_PROPERTYPUT, property_name, [property_value])

        if hard_check is True:
            assert self.get(property_name, []) == property_value

        return res

    def call(self, method_name, method_vars):
        """
        Calls a method
        :param method_name: the name of the method
        :param method_vars: a list of variables
        :return:
        """
        return self.__invoke(DISPATCH_METHOD, method_name, method_vars)
