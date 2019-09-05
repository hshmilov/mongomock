import os
import mailbox
import errno

from services.standalone_services.smtp_server import SMTPService


def create_maildir_folders():
    try:
        os.makedirs('/tmp/mail_dir/new/')
    except OSError as exc:  # Guard against race condition
        if exc.errno != errno.EEXIST:
            raise
    try:
        os.makedirs('/tmp/mail_dir/cur/')
    except OSError as exc:  # Guard against race condition
        if exc.errno != errno.EEXIST:
            raise
    try:
        os.makedirs('/tmp/mail_dir/tmp/')
    except OSError as exc:  # Guard against race condition
        if exc.errno != errno.EEXIST:
            raise


class MailDiranasaurusService(SMTPService):

    @property
    def name(self):
        return 'maildiranasaurus'

    def get_dockerfile(self, *args, **kwargs):
        return fr'''
          FROM golang:1.11.2

           WORKDIR /go/src
           RUN curl https://raw.githubusercontent.com/golang/dep/master/install.sh | sh

           RUN git clone --depth=50 --branch=master https://github.com/flashmob/maildiranasaurus.git github.com/flashmob/maildiranasaurus

           WORKDIR /go/src/github.com/flashmob/maildiranasaurus

           RUN make dependencies

           RUN make maildiranasaurus || echo dependencies failed

           COPY goguerrilla ./

           CMD ["/go/src/github.com/flashmob/maildiranasaurus/maildiranasaurus", "serve"]
           '''[1:]

    def get_email_first_csv_content(self, recipient):
        """
        Get the first csv attachment content of the mail that was sent
        :return:
        """
        mail_name, _, _ = self.get_folder_content_from_container('/tmp/mail_dir/new')
        file_name = mail_name.decode('utf-8').strip()
        out, _, _ = self.get_file_contents_from_container(f'/tmp/mail_dir/new/{file_name}')
        assert out

        create_maildir_folders()

        local_file_name = f'/tmp/mail_dir/new/{file_name}'

        with open(local_file_name, 'wb') as file:
            file.write(out)

        m = mailbox.Maildir('/tmp/mail_dir')
        payload = None
        for key in m.iterkeys():
            message = m.get_message(key)
            if message.get('To') != recipient:
                continue
            for attachment in message.get_payload():
                if attachment.get_content_type() == 'text/csv':
                    payload = attachment.get_payload(decode=True)
                    break
        m.clear()
        return payload

    @property
    def image(self):
        return 'maildiranasaurus_server'
