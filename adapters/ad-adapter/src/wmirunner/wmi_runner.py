"""
The following file implements wmi queries. It uses python2 and the impacket external library.
Since we usually use python3, it is intended to be run as a subprocess.

Note! We only support username & password right now. Hashes, nopass, kerberos auth, aes-key or rpc-auth level
were ommited. To see how to use them, see "wmiexec.py" or "wmiquery.py" in impacket/examples.

The following also have three advantages:
1. It can execute multiple queries/methods on the same connection.
2. It minimizes the size by reducing not important info we get from impacket.
3. It handles failing commands to return the rest of the commands if we have multiple(1).
"""

__author__ = "Avidor Bartov"

import argparse
import sys
import os
import json

from impacket.examples import logger
from impacket import version
from impacket.dcerpc.v5.dtypes import NULL
from impacket.dcerpc.v5.dcom import wmi
from impacket.dcerpc.v5.dcomrt import DCOMConnection
from impacket.dcerpc.v5.rpcrt import RPC_C_AUTHN_LEVEL_PKT_PRIVACY, RPC_C_AUTHN_LEVEL_PKT_INTEGRITY, \
    RPC_C_AUTHN_LEVEL_NONE


class WMIRunner(object):
    """
    Runs WMI queries and methods on a given host.
    """

    def __init__(self, address, username, password, domain='', dc_ip=None, lmhash='', nthash='', aes_key=None,
                 use_kerberos=False, rpc_auth_level="default", namespace="//./root/cimv2"):
        """
        Initializes a WMIRunner object.
        :param address: the ip of the host we are connecting to.
        :param username: The username we use.
        :param password: The password of that username.
        :param domain: The domain we are connecting to. This is usually needed, but not always.
        :param dc_ip: The ip of the dc. Optional.
        :param lmhash: part of NTLM Hashes. optional auth method.
        :param nthash: part of NTLM Hashes. optional auth method.
        :param aes_key: aes key for kerberos auth. optional auth method.
        :param use_kerberos: Use Kerberos authentication. Grabs credentials from ccache file (KRB5CCNAME)
                             based on target parameters. If valid credentials cannot be found, it will use the
                             credentials given in the initialization.
        :param rpc_auth_level: defaults to "default", but can be integrity (RPC_C_AUTHN_LEVEL_PKT_INTEGRITY) or
                               privacy (RPC_C_AUTHN_LEVEL_PKT_PRIVACY).
        :param namespace: the wmi namespace.
        """

        self.address = address
        self.username = username
        self.password = password
        self.domain = domain
        self.dc_ip = dc_ip
        self.lmhash = lmhash
        self.nthash = nthash
        self.aes_key = aes_key
        self.use_kerberos = use_kerberos
        self.rpc_auth_level = rpc_auth_level
        self.namespace = namespace
        self.dcom = None
        self.iWbemServices = None

        if aes_key is not None:
            self.use_kerberos = True

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def __del__(self):
        self.close()

    def execmethod(self, object_name, method_name, *args):
        """
        Executes a wmi method with the given args and returns the result.
        e.g. rv = o.execmethod("Win32_Process", "Create", "notepad.exe", "c:\\", None)
        print(rv['ProcessId']['value'])

        :param object_name: the wmi object.
        :param method_name: the method.
        :param args: a list of args to give the method.
        :return: an object that represents the answer.
        """

        object, _ = self.iWbemServices.GetObject(object_name)
        method = getattr(object, method_name)
        handle = method(*args)
        result = handle.getProperties()

        # If its not a list, return it as a list, to be in the same standard as execquery.
        if not isinstance(result, list):
            return [result]
        else:
            return result

    def execquery(self, query):
        """
        Executes a query.
        :param query: a wql string representing the query.
        :return: a list of objects representing the results of the query.
        """

        line = query.strip('\n')
        if line[-1:] == ';':
            line = line[:-1]
        iEnumWbemClassObject = self.iWbemServices.ExecQuery(line)

        records = []
        while True:
            try:
                pEnum = iEnumWbemClassObject.Next(0xffffffff, 1)[0]
                records.append(pEnum.getProperties())
            except Exception as e:
                if str(e).find('S_FALSE') < 0:
                    raise
                else:
                    break

        iEnumWbemClassObject.RemRelease()
        return records

    def connect(self):
        """
        Just tries to connect to the host.
        :return: True on successful connection, or exception otherwise.
        """

        dcom = DCOMConnection(self.address, self.username, self.password, self.domain, self.lmhash, self.nthash,
                              self.aes_key, oxidResolver=True, doKerberos=self.use_kerberos, kdcHost=self.dc_ip)

        iInterface = dcom.CoCreateInstanceEx(wmi.CLSID_WbemLevel1Login, wmi.IID_IWbemLevel1Login)
        iWbemLevel1Login = wmi.IWbemLevel1Login(iInterface)
        iWbemServices = iWbemLevel1Login.NTLMLogin(self.namespace, NULL, NULL)
        if self.rpc_auth_level == 'privacy':
            iWbemServices.get_dce_rpc().set_auth_level(RPC_C_AUTHN_LEVEL_PKT_PRIVACY)
        elif self.rpc_auth_level == 'integrity':
            iWbemServices.get_dce_rpc().set_auth_level(RPC_C_AUTHN_LEVEL_PKT_INTEGRITY)

        iWbemLevel1Login.RemRelease()

        self.iWbemServices = iWbemServices
        self.dcom = dcom

    def close(self):
        """
        Closes the connection.
        :return: None
        """

        try:
            self.iWbemServices.RemRelease()
            self.dcom.disconnect()
        except:
            pass


def minimize_and_convert(result):
    # the object returned by w.query is an object that contains some strings. some of them are regular,
    # and some of them are utf-16. if we try to json.dumps a utf-16 string without mentioning encoding="utf-16",
    # an exception will be thrown. on the other side if we mention encoding="utf-16" and have an str("abc")
    # an exception will be thrown as well, because str("abc") is not a utf-16 encoded string, unicode("abc") is.
    # to cut the long story short - we have multiple encodings in our object, we gotta transform everything possible
    # to unicode(s) or s.decode("utf-16")
    def convert(input):
        if isinstance(input, dict):
            return {convert(key): convert(value) for key, value in input.iteritems()}
        elif isinstance(input, list):
            return [convert(element) for element in input]
        elif isinstance(input, str):
            try:
                return unicode(input)
            except UnicodeDecodeError:
                # Its probably utf-16
                return input.decode("utf-16", errors="ignore")
        else:
            return input

    # Also, We have a lot of "garbage" returned by impacket. we only need the "name", "value" combination,
    # so lets reduce so very large amount of data.
    minified_result = []

    # For each result of a command -> for each line in the result -> for each column in a line -> get the value.
    for command_result in result:
        minified_command_result = []
        for line in command_result:
            new_line = {}
            for column_name, column_value in line.items():
                new_line[column_name] = column_value.get("value")

            minified_command_result.append(new_line)

        minified_result.append(minified_command_result)

    return convert(minified_result)


if __name__ == '__main__':
    _, domain, username, password, address, commands = sys.argv

    # Commands is a json formatted list of commands.
    commands = json.loads(commands)
    final_result_array = []

    with WMIRunner(address, username, password, domain=domain) as w:

        for command in commands:
            command_type, command_args = (command['type'], command['args'])

            # command args is a list we send to the func.
            try:
                if command_type == "query":
                    result = w.execquery(*command_args)

                elif command_type == "method":
                    result = w.execmethod(*command_args)

                else:
                    raise ValueError("command type {0} does not exist".filter(command_type))
            except Exception as e:
                result = [{"Exception": {"value": repr(e)}}]

            final_result_array.append(result)

    # To see it normally, change to(json.dumps("", indent=4)
    print json.dumps(minimize_and_convert(final_result_array), encoding="utf-16")
    sys.stdout.flush()

    sys.exit(0)
