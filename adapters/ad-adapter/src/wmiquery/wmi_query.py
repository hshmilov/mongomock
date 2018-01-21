"""
The following file implements wmi queries. It uses python2 and the impacket external library.
Since we usually use python3, it is intended to be run as a subprocess.

Note! We only support username & password right now. Hashes, nopass, kerberos auth, aes-key or rpc-auth level
were ommited. To see how to use them, see "wmiexec.py" or "wmiquery.py" in impacket/examples.
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
    Runs WMI queries on a given host.
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

    def query(self, query):
        """
        Runs a query.
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


if __name__ == '__main__':

    _, domain, username, password, address, command = sys.argv

    with WMIRunner(address, username, password, domain=domain) as w:

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

        # To see it normally, change to(json.dumps("", indent=4)
        print json.dumps(convert(w.query(command)), encoding="utf-16")
        sys.stdout.flush()

    sys.exit(0)
