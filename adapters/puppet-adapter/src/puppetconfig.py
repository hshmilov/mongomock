"""puppetconfig.py: Configuration file for the Puppet plugin."""

__author__ = "Ofri Shur"

""" The attributes we want to export from the puppet server db and their alias in our server. """
DEVICE_ATTRIBUTES = {u'certname': "DeviceName",
                     "certname": "DeviceName",
                     "operatingsystem": "operatingsystem",
                     "ipaddress": "ipaddress",
                     "osfamily": "osfamily",
                     "kernel": "kernel",
                     "macaddress": "macaddress",
                     "network": "network",
                     "network6": "network6",
                     "is_virtual": "is_virtual"}

""" The location of the certificates directory"""
RELATIVE_SSL_DIRECTORY_LOCATION = "ssl"

""" The prefix of the certificates we create in the Puppet Server """
CERTIFICATE_PREFIX_IN_PUPPET_SERVER = "axonius-certificate-"

""" Puppet connection method """
PUPPET_CONNECTION_METHOD = "https://"

""" The port for quering from the PuppetDb """
PUPPET_PORT_STRING = ":8081"

""" Location of the CA certificate of the PuppetDb query interface in the server """
CA_FILE_PUPPET_SERVER_PATH = "/etc/puppetlabs/puppet/ssl/certs/ca.pem"

""" Relative location of ssl certificates """
CERTS_FILES_DIRECTORY = "certs"

""" Relative location of the pricate keys certificates """
PRIVATE_KEYS_DIRECTORY = "private_keys"

""" Name of the ca certificate file """
CA_FILE_NAME = "ca.pem"

""" Certificates files suffix """
CERTIFICATES_SUFFIX = ".pem"

""" Puppet command to clean a certificate in the server  """
CERTIFICATES_CLEAN_COMMAN = "sudo -S /opt/puppetlabs/bin/puppet cert clean "

""" Puppet command to create new certificates in the server """
CERTIFICATES_CREATE_COMMAND = "sudo -S /opt/puppetlabs/bin/puppet cert generate "

""" Private keys location in the puppet server """
PRIVATE_KEYS_LOCATION_IN_PUPPET_SERVER = "/etc/puppetlabs/puppet/ssl/private_keys/"
""" Certficates location in puppet server """
CERTIFICATE_LOCATION_IN_PUPPET_SERVER = "/etc/puppetlabs/puppet/ssl/certs/"

""" A command to make a file read/write to everyone """
MAKE_FILE_READ_WRITE_TO_EVERYONE_COMMAND = "sudo -S chmod 666 "

""" A prefix to the Puppet REST API """
PUPPET_API_PREFIX = "/pdb/query/v4"
