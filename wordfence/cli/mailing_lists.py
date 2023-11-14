from enum import Enum


class MailingList(Enum):

    TERMS = (
            'https://www.wordfence.com/products/wordfence-cli/#terms'
        )
    WORDPRESS_SECURITY = (
            'https://www.wordfence.com/subscribe-to-the-wordfence-email-list/'
        )

    def __init__(self, registration_url):
        self.registration_url = registration_url


EMAIL_SIGNUP_MESSAGE = (
    "Register to receive updated Wordfence CLI Terms of Service via email "
    f"at {MailingList.TERMS.registration_url}. Join our WordPress Security "
    f"mailing list at {MailingList.WORDPRESS_SECURITY.registration_url} "
    "to get security alerts, news, and research directly to your inbox."
)
