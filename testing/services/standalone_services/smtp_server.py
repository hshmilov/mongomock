import os
import uuid

from typing import Iterable
from retrying import retry

from services.docker_service import DockerService
from services.ports import DOCKER_PORTS


def generate_random_valid_email() -> str:
    """
    Generates a valid, random and unique email address
    """
    return f'{uuid.uuid4().hex}@avigdor.ru'


class SMTPService(DockerService):
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

    def get_dockerfile(self, mode=''):
        return fr'''
        FROM golang:1.11.2
             
        WORKDIR /go/src/app
        RUN curl https://glide.sh/get | sh
        RUN git clone https://github.com/flashmob/go-guerrilla.git || echo failed

        WORKDIR /go/src/app/go-guerrilla
        
        RUN glide install
        RUN make dependencies || echo dependencies failed
        RUN make guerrillad | echo guerrillad failed
        
        # it fails if you don't play with it, like a lovely girl, you need to persuade it
        
        RUN make dependencies || echo dependencies failed
        RUN make guerrillad || echo guerrillad failed
        
        COPY goguerrilla ./
        
        CMD ["/go/src/app/go-guerrilla/guerrillad", "serve"]
        '''[1:]

    @retry(stop_max_attempt_number=100, wait_fixed=100)
    def verify_email_send(self, recipient: str):
        """
        Verifies that an email has been sent to the given address
        :param recipient: the email address that the email was sent to
        """
        last_log = list(self.get_emails_sent())[-10:]
        assert any(bytes(recipient, 'ascii') in l for l in last_log)

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
        return 'golang:1.11.2'
