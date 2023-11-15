import sys

from wordfence.util.input import prompt_yes_no, InputException
from wordfence.util.caching import Cacheable, NoCachedValueException, \
        DURATION_ONE_DAY
from .context import CliContext

TERMS_URL = \
    'https://www.wordfence.com/wordfence-cli-license-terms-and-conditions/'
TERMS_CACHE_KEY = 'terms'
ACCEPTANCE_CACHE_KEY = 'terms-accepted'


class TermsManager:

    def __init__(self, context: CliContext):
        self.context = context

    def prompt_acceptance_if_needed(self):
        try:
            accepted = self.context.cache.get(ACCEPTANCE_CACHE_KEY)
            if accepted:
                return
        except NoCachedValueException:
            pass
        self.prompt_acceptance()

    def trigger_update(self, paid: bool = False):
        self.context.cache.remove(TERMS_CACHE_KEY)
        self.context.cache.put(ACCEPTANCE_CACHE_KEY, False)
        self.prompt_acceptance(paid)

    def record_acceptance(self, remote: bool = True):
        if remote:
            client = self.context.get_noc1_client()
            client.record_toupp()
        self.context.cache.put(ACCEPTANCE_CACHE_KEY, True)

    def prompt_acceptance(self, paid: bool = False):
        if self.context.config.accept_terms:
            self.record_acceptance()
            return
        if paid:
            edition = ''
        else:
            edition = ' Free edition'
        terms_accepted = False
        try:
            terms_accepted = prompt_yes_no(
                f'Your access to and use of Wordfence CLI{edition} is '
                'subject to the updated Wordfence CLI License Terms and '
                f'Conditions set forth at {TERMS_URL}. By entering "y" and '
                'selecting Enter, you agree that you have read and accept the '
                'updated Wordfence CLI License Terms and Conditions.',
                default=False
            )
        except InputException:
            print(
                    'Wordfence CLI does not appear to be running interactively'
                    ' and cannot prompt for agreement to the license terms. '
                    'Please run Wordfence CLI in a terminal or use the '
                    '--accept-terms command line option instead.'
                )
        if terms_accepted:
            self.record_acceptance()
        else:
            print(
                    'You must accept the terms in order to continue using'
                    ' Wordfence CLI.'
                )
            sys.exit(1)

    def _fetch_terms(self) -> str:
        client = self.context.get_noc1_client()
        return client.get_terms()

    def get_terms(self) -> str:
        cacheable = Cacheable(
                TERMS_CACHE_KEY,
                self._fetch_terms,
                DURATION_ONE_DAY
            )
        return cacheable.get(self.context.cache)
