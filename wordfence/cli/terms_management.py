import sys

from wordfence.util.input import prompt_yes_no, InputException
from wordfence.util.caching import Cacheable, NoCachedValueException, \
        InvalidCachedValueException, DURATION_ONE_DAY
from wordfence.api.licensing import License, LicenseSpecific
from .context import CliContext
from .licensing import LicenseManager

TERMS_URL = \
    'https://www.wordfence.com/wordfence-cli-license-terms-and-conditions/'
TERMS_CACHE_KEY = 'terms'
ACCEPTANCE_CACHE_KEY = 'terms-accepted'
CACHEABLE_TYPES = {
        'wordfence.cli.terms_management.LicenseTermsAcceptance'
    }


class LicenseTermsAcceptance(LicenseSpecific):

    def __init__(self, license: License, accepted: bool = False):
        super().__init__(license)
        self.accepted = accepted


class TermsManager:

    def __init__(self, context: CliContext, license_manager: LicenseManager):
        self.context = context
        self.license_manager = license_manager

    def prompt_acceptance_if_needed(self, use_api: bool = True):
        try:
            acceptance = self.context.cache.get(ACCEPTANCE_CACHE_KEY)
            if acceptance is True:
                self.record_acceptance(remote=False)
                return
            if acceptance.accepted:
                return
        except (NoCachedValueException, InvalidCachedValueException):
            if use_api:
                client = self.context.get_noc1_client()
                client.ping_api_key()
                self.prompt_acceptance_if_needed(False)
                return
        self.prompt_acceptance(license=self.license_manager.check_license())

    def _cache_acceptance(
                self,
                license: License,
                accepted: bool = True
            ):
        self.context.cache.put(
                ACCEPTANCE_CACHE_KEY,
                LicenseTermsAcceptance(license, accepted)
            )

    def record_acceptance(
                self,
                license: License = None,
                accepted: bool = True,
                remote: bool = True
            ) -> None:
        if license is None:
            license = self.license_manager.check_license()
        if remote:
            client = self.context.create_noc1_client(license)
            client.record_toupp()
        self._cache_acceptance(license, accepted)

    def trigger_update(self, updated: bool, license: License):
        if updated:
            self.context.cache.remove(TERMS_CACHE_KEY)
        self.record_acceptance(
                license=license,
                accepted=not updated,
                remote=False
            )
        if updated:
            self.prompt_acceptance(license)

    def prompt_acceptance(self, license: License):
        if self.context.config.accept_terms:
            self.record_acceptance(license=license)
            return
        if license.paid:
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
            self.record_acceptance(license=license)
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
