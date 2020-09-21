import datetime
import html
import logging
import urllib.parse
from pathlib import Path

import OpenSSL
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
from bson import ObjectId
from flask import request, Response
from flask.json import jsonify

from axonius.consts.core_consts import CORE_CONFIG_NAME
from axonius.consts.gui_consts import GUI_CONFIG_NAME, FeatureFlagsNames
from axonius.consts.plugin_consts import CORE_UNIQUE_NAME
from axonius.plugin_base import return_error
from axonius.utils.permissions_helper import PermissionCategory
from axonius.utils.ssl import check_associate_cert_with_private_key, validate_cert_with_ca, SSL_CERT_PATH
from gui.logic.routing_helper import gui_category_add_rules, gui_route_logged_in
# pylint: disable=no-member,access-member-before-definition

logger = logging.getLogger(f'axonius.{__name__}')

GLOBAL_SSL_KEY = 'global_ssl'
SSL_TRUST_KEY = 'ssl_trust_settings'
MUTUAL_TLS_KEY = 'mutual_tls_settings'
CSR_KEY = 'csr_settings'


@gui_category_add_rules('certificate', permission_category=PermissionCategory.Settings)
class Certificate:
    ##################
    # Certificate Service #
    ##################
    @gui_route_logged_in('details', methods=['GET'], enforce_trial=True)
    def check_certificate_details(self):
        config_cert = self._grab_file_contents(self._global_ssl.get('cert_file', None), stored_locally=False)
        if not config_cert or not self._global_ssl.get('enabled', False):
            config_cert = Path(SSL_CERT_PATH).read_text()
        parsed_cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, config_cert)
        return jsonify({
            'issued_to': html.escape(parsed_cert.get_subject().CN),
            'alternative_names': self._find_subjectAltName(parsed_cert),
            'issued_by':
                '/'.join([html.escape(x[1].decode('utf-8')) for x in parsed_cert.get_issuer().get_components()]),
            'sha1_fingerprint': parsed_cert.digest('sha1').decode('utf-8'),
            'expires_on': datetime.datetime.strptime(parsed_cert.get_notAfter().decode('utf-8'), '%Y%m%d%H%M%SZ')
        })

    @gui_route_logged_in('reset_to_defaults', methods=['POST'], enforce_trial=True)
    def reset_to_defaults(self):
        try:
            self.plugins.core.configurable_configs.update_config(
                CORE_CONFIG_NAME,
                {
                    f'{GLOBAL_SSL_KEY}.enabled': False,
                    f'{GLOBAL_SSL_KEY}.cert_file': '',
                    f'{GLOBAL_SSL_KEY}.private_key': '',
                    f'{GLOBAL_SSL_KEY}.passphrase': '',
                    f'{GLOBAL_SSL_KEY}.hostname': ''
                }
            )
            self._reset_csr()
            self._update_config_inner()
            return jsonify(True)
        except Exception:
            return return_error('Error while resetting certificate settings', 400)

    @gui_route_logged_in('import_cert', methods=['POST'], enforce_trial=True)
    def import_cert(self):
        cert_file = request.get_json()
        if cert_file:
            try:
                csr_req = self.plugins.get_plugin_settings(CORE_UNIQUE_NAME).configurable_configs[
                    CORE_CONFIG_NAME][CSR_KEY]
                private_key_obj = OpenSSL.crypto.load_privatekey(OpenSSL.crypto.FILETYPE_PEM,
                                                                 self._grab_file_contents(csr_req.get('key_file'),
                                                                                          stored_locally=False))
                cert_obj = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM,
                                                           self._grab_file_contents(cert_file,
                                                                                    stored_locally=False))
                context = OpenSSL.SSL.Context(OpenSSL.SSL.TLSv1_METHOD)
                context.use_privatekey(private_key_obj)
                context.use_certificate(cert_obj)

                context.check_privatekey()
                # The certificate match the private key, we have a key pair!!!
                self.plugins.core.configurable_configs.update_config(
                    CORE_CONFIG_NAME,
                    {
                        f'{GLOBAL_SSL_KEY}.enabled': True,
                        f'{GLOBAL_SSL_KEY}.cert_file': cert_file,
                        f'{GLOBAL_SSL_KEY}.private_key': csr_req.get('key_file'),
                        f'{GLOBAL_SSL_KEY}.passphrase': '',
                        f'{GLOBAL_SSL_KEY}.hostname': cert_obj.get_subject().CN
                    }
                )
                self._reset_csr()
                self._update_config_inner()
            except OpenSSL.SSL.Error:
                return return_error('Certificate does not match private key on server', 400)
            except Exception:
                return return_error('Error occurred while checking imported certificate file', 400)
            return jsonify(True)
        return return_error('Import certificate request not according to schema', 400)

    @gui_route_logged_in('cancel_csr', methods=['POST'], enforce_trial=True)
    # pylint: disable=lost-exception
    def cancel_csr(self):
        try:
            csr_req = self.plugins.get_plugin_settings(CORE_UNIQUE_NAME).configurable_configs[CORE_CONFIG_NAME][CSR_KEY]
            self.db_files.delete_file(ObjectId(csr_req.get('csr_file', {}).get('uuid', None)))
            self.db_files.delete_file(ObjectId(csr_req.get('key_file', {}).get('uuid', None)))
        except Exception:
            logger.error('Error while deleting old csr and key files', exc_info=True)
        finally:
            return jsonify(self._reset_csr())

    @gui_route_logged_in('csr', methods=['GET', 'POST'], enforce_trial=True)
    # pylint: disable=too-many-return-statements,too-many-branches,too-many-statements
    def csr(self):
        csr_req = self.plugins.get_plugin_settings(CORE_UNIQUE_NAME).configurable_configs[CORE_CONFIG_NAME][CSR_KEY]
        # Returns the CSR file stored in db and return to the user to download
        if request.method == 'GET':
            headers = {
                'Content-Disposition': f'attachment; filename=cert.csr',
                'Content-Type': 'text/plain'
            }
            try:
                csr_file = self._grab_file_contents(csr_req.get('csr_file'), stored_locally=False)
            except Exception:
                return return_error('Couldn\'t get csr file from db', 400)
            return Response(csr_file, headers=headers)

        # Means its a POST request with CSR creation details
        csr_request = None
        try:
            csr_request = request.get_json()
            if csr_request:
                if self.feature_flags_config().get(FeatureFlagsNames.DisableRSA, False):
                    # Generate Private key
                    key = ec.generate_private_key(ec.SECP384R1(), default_backend())
                    key_pem = key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.PKCS8,
                        encryption_algorithm=serialization.NoEncryption()
                    )
                    x509attributes = [x509.NameAttribute(NameOID.COMMON_NAME, csr_request['hostname'])]
                    if csr_request['country'] and len(csr_request['country']) != 2:
                        return return_error('Country must be only 2 letters', 400)
                    if csr_request['country']:
                        x509attributes.append(x509.NameAttribute(NameOID.COUNTRY_NAME, csr_request['country']))
                    if csr_request['state']:
                        x509attributes.append(x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, csr_request['state']))
                    if csr_request['location']:
                        x509attributes.append(x509.NameAttribute(NameOID.LOCALITY_NAME, csr_request['location']))
                    if csr_request['organization']:
                        x509attributes.append(x509.NameAttribute(NameOID.ORGANIZATION_NAME,
                                                                 csr_request['organization']))
                    if csr_request['OU']:
                        x509attributes.append(x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, csr_request['OU']))
                    if csr_request['email']:
                        x509attributes.append(x509.NameAttribute(NameOID.EMAIL_ADDRESS, csr_request['email']))

                    x509altnames = [x509.DNSName(csr_request['hostname'])]
                    # pylint: disable=expression-not-assigned
                    [x509altnames.append(x509.DNSName(alt_name)) for alt_name in csr_request['alt_names'].split(';')]

                    csr = x509.CertificateSigningRequestBuilder().subject_name(x509.Name(x509attributes)).add_extension(
                        x509.SubjectAlternativeName(x509altnames),
                        critical=False,
                        # Sign the CSR with our private key.
                    ).sign(key, hashes.SHA256(), default_backend())
                    csr_pem = csr.public_bytes(serialization.Encoding.PEM)
                else:
                    key = OpenSSL.crypto.PKey()
                    key.generate_key(OpenSSL.crypto.TYPE_RSA, 4096)
                    key_pem = OpenSSL.crypto.dump_privatekey(OpenSSL.crypto.FILETYPE_PEM, key)

                    # Generate CSR
                    csr = OpenSSL.crypto.X509Req()
                    csr.get_subject().CN = csr_request['hostname']
                    if csr_request['country']:
                        try:
                            csr.get_subject().C = csr_request['country']
                        except OpenSSL.crypto.Error:
                            return return_error('Country must be only 2 letters', 400)
                    if csr_request['state']:
                        csr.get_subject().ST = csr_request['state']
                    if csr_request['location']:
                        csr.get_subject().L = csr_request['location']
                    if csr_request['organization']:
                        csr.get_subject().O = csr_request['organization']
                    if csr_request['OU']:
                        csr.get_subject().OU = csr_request['OU']
                    if csr_request['email']:
                        csr.get_subject().emailAddress = csr_request['email']
                    alt_names = [f'DNS: {alt_name.strip()}' for alt_name in csr_request['alt_names'].split(';')]
                    base_constraints = ([
                        OpenSSL.crypto.X509Extension(b'keyUsage', False,
                                                     b'Digital Signature, Non Repudiation, Key Encipherment'),
                        OpenSSL.crypto.X509Extension(b'basicConstraints', False, b'CA:FALSE'),
                    ])
                    if alt_names != ['DNS: ']:
                        base_constraints.append(
                            OpenSSL.crypto.X509Extension(b'subjectAltName', False, ', '.join(alt_names).
                                                         encode('utf-8')))
                    csr.add_extensions(base_constraints)
                    csr.set_pubkey(key)
                    csr.sign(key, 'sha256')
                    csr_pem = OpenSSL.crypto.dump_certificate_request(OpenSSL.crypto.FILETYPE_PEM, csr)

                csr_uuid = self.db_files.upload_file(csr_pem, filename='cert.csr')
                key_uuid = self.db_files.upload_file(key_pem, filename='cert.key')

                self.plugins.core.configurable_configs.update_config(
                    CORE_CONFIG_NAME,
                    {
                        f'{CSR_KEY}.status': True,
                        f'{CSR_KEY}.subject_name': csr_request['hostname'],
                        f'{CSR_KEY}.submission_date': datetime.datetime.now().strftime('%Y/%m/%d'),
                        f'{CSR_KEY}.csr_file': {'uuid': csr_uuid, 'filename': 'cert.csr'},
                        f'{CSR_KEY}.key_file': {'uuid': key_uuid, 'filename': 'cert.key'}
                    }
                )
                return jsonify(True)
            return return_error('CSR schema not as requested', 400)
        except Exception:
            logger.error(f'Error occurred while generating CSR: {csr_request}', exc_info=True)
            return return_error('Error occurred while generating CSR', 400)

    def _reset_csr(self):
        try:
            self.plugins.core.configurable_configs.update_config(
                CORE_CONFIG_NAME,
                {
                    f'{CSR_KEY}.status': False,
                    f'{CSR_KEY}.subject_name': '',
                    f'{CSR_KEY}.submission_date': '',
                    f'{CSR_KEY}.csr_file': '',
                    f'{CSR_KEY}.key_file': ''
                }
            )
        except Exception:
            logger.error('Error while resetting CSR status', exc_info=True)
            return False
        return True

    @gui_route_logged_in('certificate_settings', methods=['GET', 'POST'], enforce_trial=True)
    # pylint: disable=too-many-return-statements,too-many-branches
    def check_settings(self):
        if request.method == 'GET':
            return jsonify({
                'ssl_trust': self._ssl_trust_settings,
                'mutual_tls': {}
            })
        try:
            post_data = request.get_json()
            ssl_trust_settings = post_data.get('ssl_trust', None)
            if ssl_trust_settings:
                for ca_file in ssl_trust_settings['ca_files']:
                    try:
                        OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM,
                                                        self._grab_file_contents(ca_file, stored_locally=False))
                    except OpenSSL.crypto.Error:
                        try:
                            OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_ASN1,
                                                            self._grab_file_contents(ca_file, stored_locally=False))
                        except Exception:
                            logger.error(f'Can not load ca certificate', exc_info=True)
                            return return_error(f'The uploaded file is not a pem or asn1 format certificate', 400)
                    except Exception:
                        logger.error(f'Can not load ca certificate', exc_info=True)
                        return return_error(f'The uploaded file is not a pem-format certificate', 400)
                self.plugins.core.configurable_configs.update_config(
                    CORE_CONFIG_NAME,
                    {
                        f'{SSL_TRUST_KEY}.enabled': ssl_trust_settings['enabled'],
                        f'{SSL_TRUST_KEY}.ca_files': ssl_trust_settings['ca_files']
                    }
                )

            mutual_tls_settings = post_data.get('mutual_tls', None)
            if mutual_tls_settings and mutual_tls_settings.get('enabled', False):
                is_mandatory = mutual_tls_settings.get('mandatory')
                client_ssl_cert = request.environ.get('HTTP_X_CLIENT_ESCAPED_CERT')

                if is_mandatory and not client_ssl_cert:
                    logger.error(f'Client certificate not found in request.')
                    return return_error(f'Client certificate not found in request. Please make sure your client '
                                        f'uses a certificate to access Axonius', 400)

                try:
                    ca_certificate = self._grab_file_contents(mutual_tls_settings.get('ca_certificate'))
                except Exception:
                    logger.exception(f'Error getting ca certificate from db')
                    return return_error(f'can not find uploaded certificate', 400)

                try:
                    OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, ca_certificate)
                except Exception:
                    logger.error(f'Can not load ca certificate', exc_info=True)
                    return return_error(f'The uploaded file is not a pem-format certificate', 400)
                try:
                    if is_mandatory and \
                            not validate_cert_with_ca(urllib.parse.unquote(client_ssl_cert), ca_certificate):
                        logger.error(f'Current client certificate is not trusted by the uploaded CA')
                        return return_error(f'Current client certificate is not trusted by the uploaded CA', 400)
                except Exception:
                    logger.error(f'Can not validate current client certificate with the uploaded CA', exc_info=True)
                    return return_error(f'Current client certificate can not be validated by the uploaded CA', 400)

                self.plugins.gui.configurable_configs.update_config(
                    GUI_CONFIG_NAME,
                    {
                        f'{MUTUAL_TLS_KEY}.enabled': mutual_tls_settings['enabled'],
                        f'{MUTUAL_TLS_KEY}.mandatory': mutual_tls_settings['mandatory'],
                        f'{MUTUAL_TLS_KEY}.ca_certificate': mutual_tls_settings['ca_certificate']
                    }
                )
            elif mutual_tls_settings:
                self.plugins.gui.configurable_configs.update_config(
                    GUI_CONFIG_NAME,
                    {
                        f'{MUTUAL_TLS_KEY}.enabled': False,
                        f'{MUTUAL_TLS_KEY}.mandatory': False,
                        f'{MUTUAL_TLS_KEY}.ca_certificate': ''
                    }
                )
            self._update_config_inner()
        except Exception:
            return return_error('Error while saving certificate settings', 400)
        else:
            return jsonify(True)

    @gui_route_logged_in('global_ssl', methods=['GET', 'POST'], enforce_trial=True)
    # pylint: disable=too-many-return-statements
    def global_ssl(self):
        if request.method == 'GET':
            return jsonify(self._global_ssl)
        try:
            post_data = request.get_json()
            if isinstance(post_data, dict):
                config_cert = self._grab_file_contents(post_data.get('cert_file'), stored_locally=False)
                config_private = self._grab_file_contents(post_data.get('private_key'), stored_locally=False)
                try:
                    parsed_cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, config_cert)
                except Exception:
                    logger.exception(f'Error loading certificate')
                    return return_error(
                        f'Error loading certificate file. Please upload a pem-type certificate file.', 400)
                cn = dict(parsed_cert.get_subject().get_components())[b'CN'].decode('utf8')
                if cn != post_data['hostname']:
                    return return_error(f'Hostname does not match the hostname in the certificate file, '
                                        f'hostname in given cert is {cn}', 400)

                passphrase = post_data.get('passphrase', b'')
                if passphrase == ['unchanged']:
                    passphrase = self._global_ssl['passphrase'].encode('utf-8')
                if isinstance(passphrase, str):
                    passphrase = passphrase.encode('utf-8')
                try:
                    ssl_check_result = check_associate_cert_with_private_key(
                        config_cert, config_private, passphrase
                    )
                except Exception as e:
                    return return_error(f'Error - can not load ssl settings: {str(e)}', 400)

                if not ssl_check_result:
                    return return_error(f'Private key and public certificate do not match each other', 400)

                self.plugins.core.configurable_configs.update_config(
                    CORE_CONFIG_NAME,
                    {
                        f'{GLOBAL_SSL_KEY}.enabled': post_data['enabled'],
                        f'{GLOBAL_SSL_KEY}.cert_file': post_data['cert_file'],
                        f'{GLOBAL_SSL_KEY}.private_key': post_data['private_key'],
                        f'{GLOBAL_SSL_KEY}.passphrase': post_data['passphrase'],
                        f'{GLOBAL_SSL_KEY}.hostname': post_data['hostname']
                    }
                )
                self._update_config_inner()
                return jsonify(True)
            return return_error('Import certificate and key schema not as requested', 400)
        except Exception:
            return return_error('Problem in saving Global SSL settings', 400)

    @staticmethod
    def _find_subjectAltName(cert: OpenSSL.crypto.X509):
        for i in range(cert.get_extension_count()):
            if b'subjectAltName' in cert.get_extension(i).get_short_name():
                return [html.escape(x.split(':')[1]) for x in str(cert.get_extension(i)).split(',')]
        return []
