import logging

# setup null handler for all API endpoints
logging.getLogger("uaclient").addHandler(logging.NullHandler())
