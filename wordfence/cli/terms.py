import sys

from wordfence.util.input import prompt_yes_no
from .context import CliContext

TERMS_URL = \
    'https://www.wordfence.com/wordfence-cli-license-terms-and-conditions/'
TERMS_CACHE_KEY = 'terms-accepted'


class TermsManager:

    def __init__(self, context: CliContext):
        self.context = context

    def prompt_acceptance_if_needed(self):
        accepted = self.context.cache.get(TERMS_CACHE_KEY)
        if not accepted:
            self.prompt_acceptance()

    def trigger_update(self, paid: bool = False):
        self.context.cache.put(TERMS_CACHE_KEY, False)
        self.prompt_acceptance(paid)

    def record_acceptance(self, remote: bool = True):
        if remote:
            client = self.context.get_noc1_client()
            client.record_toupp()
        self.context.cache.put(TERMS_CACHE_KEY, True)

    def prompt_acceptance(self, paid: bool = False):
        if not (sys.stdout.isatty() and sys.stdin.isatty()):
            return
        if paid:
            edition = ''
        else:
            edition = ' Free edition'
        terms_accepted = prompt_yes_no(
                f'Your access to and use of Wordfence CLI{edition} is '
                'subject to the updated Wordfence CLI License Terms and '
                f'Conditions set forth at {TERMS_URL}. By entering "y" and '
                'selecting Enter, you agree that you have read and accept the '
                'updated Wordfence CLI License Terms and Conditions.',
                default=False
            )
        if terms_accepted:
            self.record_acceptance()
        else:
            print(
                    'You must accept the terms in order to continue using'
                    ' Wordfence CLI.'
                )
            sys.exit(1)
