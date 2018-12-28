import os
from typing import Iterable

from services.weave_service import WeaveService


class SyslogService(WeaveService):
    def __init__(self):
        super().__init__(self.name, '')
        self.__syslog_dir = os.path.abspath(os.path.join(self.log_dir, 'syslogs/'))
        if not os.path.exists(self.__syslog_dir):
            os.makedirs(self.__syslog_dir)

        self.__conf_file = os.path.abspath(
            os.path.join(self.cortex_root_dir, 'testing', 'services', 'standalone_services', 'syslog-ng.conf'))

    def is_up(self):
        return True

    @property
    def name(self):
        return 'syslog'

    def get_dockerfile(self, mode=''):
        return r'''
    FROM balabit/syslog-ng:latest
    RUN apt-get update && apt-get install -y openssl
    WORKDIR /usr/local/etc
    RUN mkdir syslog-ng
    WORKDIR /usr/local/etc/syslog-ng
    RUN touch index.txt
    RUN echo 00 > serial
    RUN cp /etc/ssl/openssl.cnf openssl.cnf
    RUN sed -i 's/\.\/demoCA/\./g' openssl.cnf
    RUN mkdir certs crl newcerts private
    RUN openssl req -new -x509 -keyout private/cakey.pem -out cacert.pem -config openssl.cnf -subj "/C=IL/ST=Axonius/L=TLV/O=Dis/CN=www.axonius.com" -passout pass:1234
    RUN openssl req -nodes -new -x509 -keyout serverkey.pem -out serverreq.pem -config openssl.cnf -subj "/C=IL/ST=Axonius/L=TLV/O=Dis/CN=www.axonius.com"
    RUN openssl x509 -x509toreq -in serverreq.pem -signkey serverkey.pem -out tmp.pem
    RUN openssl ca -batch -keyfile private/cakey.pem -passin pass:1234 -config openssl.cnf -policy policy_anything -out servercert.pem -infiles tmp.pem
    RUN mkdir cert.d ca.d
    RUN cp serverkey.pem cert.d
    RUN cp servercert.pem cert.d
    RUN cp cacert.pem ca.d
    RUN openssl x509 -noout -hash -in cacert.pem | xargs -I '{}' ln -s cacert.pem '{}'.0
    '''[1:]

    def get_main_file(self):
        return ''

    @property
    def volumes_override(self):
        return [
            f'{self.__syslog_dir}:/var/log/syslog-ng',
            f'{self.__conf_file}:/etc/syslog-ng/syslog-ng.conf'
        ]

    def get_syslog_data(self) -> Iterable[str]:
        """
        Get all lines from the syslog
        """
        out, _, _ = self.get_file_contents_from_container('/var/log/syslog-ng/syslog.log')
        return out.splitlines()

    @property
    def volumes(self):
        return []

    @property
    def exposed_ports(self):
        return []

    @property
    def image(self):
        return 'balabit/syslog-ng'

    @property
    def tcp_port(self):
        return 514

    @property
    def tls_port(self):
        return 6514
