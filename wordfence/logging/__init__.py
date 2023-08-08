import logging

DEFAULT_LOGGER_NAME = 'wordfence'

logging.basicConfig(format='%(message)s')
log = logging.getLogger(DEFAULT_LOGGER_NAME)
