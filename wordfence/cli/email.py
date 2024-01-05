import smtplib
from email.message import Message
from email.headerregistry import Address
from enum import Enum
from typing import Optional
from os import popen, getuid
from socket import gethostname
from pwd import getpwuid

from ..logging import log
from .config.config import Config


class EmailException(Exception):
    pass


class SmtpTlsMode(Enum):
    NONE = 'none'
    SMTPS = 'smtps'
    STARTTLS = 'starttls'


class Sender:

    def send(self, message: Message) -> None:
        pass

    def close(self) -> None:
        pass


class SmtpSender(Sender):

    def __init__(
                self,
                host: str,
                port: Optional[int] = None,
                tls_mode: SmtpTlsMode = SmtpTlsMode.STARTTLS,
                user: Optional[str] = None,
                password: Optional[str] = None
            ):
        smtp_type = smtplib.SMTP_SSL if tls_mode is SmtpTlsMode.SMTPS \
            else smtplib.SMTP
        port = 0 if port is None else port
        try:
            self.smtp = smtp_type(
                    host=host,
                    port=port
                )
            if tls_mode is SmtpTlsMode.STARTTLS:
                log.debug('Starting SMTP TLS...')
                self.smtp.starttls()
            if user is not None:
                log.debug(f'Authenticating with SMTP server as {user}...')
                self.smtp.login(user, password)
        except smtplib.SMTPException as e:
            raise EmailException('SMTP client creation failed') from e

    def send(self, message: Message) -> None:
        try:
            log.debug(f"Sending email via SMTP to {message['To']}...")
            self.smtp.send_message(message)
        except smtplib.SMTPException as e:
            raise EmailException('Sending email via SMTP failed') from e

    def close(self) -> None:
        self.smtp.quit()


class SendmailSender(Sender):

    def __init__(self, executable: str):
        self.executable = executable

    def send(self, message: Message):
        log.debug(f"Sending email via sendmail to {message['To']}...")
        command = f'{self.executable} -t -oi'
        try:
            sendmail = popen(command, 'w')
            sendmail.write(message.as_string())
            result = sendmail.close()
            if result is not None:
                raise EmailException(f'Sendmail exited with code: {result}')
        except Exception as e:
            raise EmailException('Sendmail invocation failed') from e


def initialize_sender(config: Config) -> Sender:
    if config.smtp_host is None:
        return SendmailSender(config.sendmail_path)
    else:
        return SmtpSender(
                config.smtp_host,
                config.smtp_port,
                SmtpTlsMode(config.smtp_tls_mode),
                config.smtp_user,
                config.smtp_password
            )


def generate_default_from_address(display_name: str) -> Address:
    username = getpwuid(getuid()).pw_name
    hostname = gethostname()
    address = Address(
            display_name=display_name,
            username=username,
            domain=hostname
        )
    return address


class Mailer(Sender):

    def __init__(
                self,
                config: Config,
            ):
        self.config = config
        self.sender = None
        self.from_address = None

    def get_sender(self) -> Sender:
        if self.sender is None:
            self.sender = initialize_sender(self.config)
        return self.sender

    def get_from_address(self) -> str:
        if self.from_address is None:
            address = self.config.email_from
            display_name = 'Wordfence CLI'
            if address is None:
                address = generate_default_from_address(display_name)
            else:
                address = Address(
                        display_name=display_name,
                        addr_spec=address
                    )
            self.from_address = str(address)
        return self.from_address

    def send(self, message: Message) -> None:
        message['From'] = self.get_from_address()
        self.get_sender().send(message)

    def close(self) -> None:
        if self.sender is not None:
            self.sender.close()
