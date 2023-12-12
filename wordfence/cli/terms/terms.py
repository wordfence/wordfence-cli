from ...util import caching
from ...logging import log
from ..subcommands import Subcommand
from ..mailing_lists import EMAIL_SIGNUP_MESSAGE


class TermsSubcommand(Subcommand):

    def fetch_terms(self) -> str:
        client = self.context.create_noc1_client(use_hooks=False)
        return client.get_terms()

    def get_terms(self) -> str:
        cacheable = caching.Cacheable(
                'terms',
                self.fetch_terms,
                caching.DURATION_ONE_DAY
            )
        return cacheable.get(self.cache)

    def invoke(self) -> int:
        terms = self.get_terms()
        print(terms)
        log.info(EMAIL_SIGNUP_MESSAGE)
        return 0


factory = TermsSubcommand
