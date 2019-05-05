import os
import uuid

from typing import Iterable
from retrying import retry

from services.ports import DOCKER_PORTS
from services.weave_service import WeaveService


def generate_random_valid_email() -> str:
    """
    Generates a valid, random and unique email address
    """
    return f'{uuid.uuid4().hex}@avigdor.ru'


class SMTPService(WeaveService):
    def __init__(self):
        super().__init__(self.name, 'services/standalone_services')
        self.__conf_dir = os.path.abspath(
            os.path.join(self.cortex_root_dir, 'testing', 'services', 'standalone_services', 'go-guerrilla')).\
            replace('\\', '/')

    def is_up(self):
        return True

    @property
    def name(self):
        return 'smtp'

    @property
    def port(self):
        return DOCKER_PORTS[self.name]

    def get_dockerfile(self, *args, **kwargs):
        return fr'''
        FROM golang:1.11.2

        WORKDIR /go/src
        RUN curl https://raw.githubusercontent.com/golang/dep/master/install.sh | sh
        
        RUN git clone --depth=50 --branch=master https://github.com/flashmob/go-guerrilla.git github.com/flashmob/go-guerrilla
        
        WORKDIR /go/src/github.com/flashmob/go-guerrilla
        
        RUN make guerrillad || echo dependencies failed

        COPY goguerrilla ./
        
        CMD ["/go/src/github.com/flashmob/go-guerrilla/guerrillad", "serve"]
        '''[1:]

    @retry(stop_max_attempt_number=200, wait_fixed=500)
    def verify_email_send(self, recipient: str):
        '''
        Verifies that an email has been sent to the given address
        :param recipient: the email address that the email was sent to
        '''
        last_log = list(self.get_emails_sent())[-10:]
        rec = bytes(recipient, 'ascii')
        assert any(rec in l for l in last_log), f'Expected to find {recipient} in {str(last_log)}'

    def get_emails_sent(self) -> Iterable[str]:
        """
        Get all lines from the syslog
        """
        out, _, _ = self.get_file_contents_from_container('/var/log/guerilla.log')
        return out.splitlines()

    def get_main_file(self):
        return ''

    @property
    def volumes(self):
        return []

    @property
    def exposed_ports(self):
        return [(DOCKER_PORTS[self.name], DOCKER_PORTS[self.name])]

    @property
    def image(self):
        return 'smtp_server'
