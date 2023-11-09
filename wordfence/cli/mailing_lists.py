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
