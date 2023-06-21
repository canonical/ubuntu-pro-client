import logging

# setup null handler for all API endpoints
logging.getLogger("ubuntupro").addHandler(logging.NullHandler())
