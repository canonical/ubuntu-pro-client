"""
This module contains URLs that are to be displayed in messages only.
URLs that are actually contacted by the pro-client should be defined elsewhere.
"""

PRO_HOME_PAGE = "https://ubuntu.com/pro"
PRO_DASHBOARD = "https://ubuntu.com/pro/dashboard"
PRO_ATTACH = "https://ubuntu.com/pro/attach"
PRO_SUBSCRIBE = "https://ubuntu.com/pro/subscribe"

PRO_CLIENT_DOCS_RELATED_USNS = "https://canonical-ubuntu-pro-client.readthedocs-hosted.com/en/latest/explanations/cves_and_usns_explained.html#what-are-related-usns"  # noqa: E501
PRO_CLIENT_DOCS_CLOUD_PRO_IMAGES = "https://canonical-ubuntu-pro-client.readthedocs-hosted.com/en/latest/explanations/what_are_ubuntu_pro_cloud_instances.html"  # noqa: E501
PRO_CLIENT_DOCS_PROXY_CONFIG = "https://canonical-ubuntu-pro-client.readthedocs-hosted.com/en/latest/howtoguides/configure_proxies.html"  # noqa: E501

# TODO: If/when `pro disable fips --purge` exists, reference that where
# this URL is used
# If that doesn't happen, write a new how-to-guide in our proper docs and
# link to that here
PRO_CLIENT_DOCS_REMOVE_FIPS = "https://discourse.ubuntu.com/t/20738"

PRO_ON_AWS_HOME_PAGE = "https://ubuntu.com/aws/pro"
PRO_ON_AZURE_HOME_PAGE = "https://ubuntu.com/azure/pro"
PRO_ON_GCP_HOME_PAGE = "https://ubuntu.com/gcp/pro"

ANBOX_HOME_PAGE = "https://anbox-cloud.io"
ANBOX_DOCS_APPLIANCE_INITIALIZE = (
    "https://anbox-cloud.io/docs/tut/installing-appliance#initialise"
)
CIS_HOME_PAGE = "https://ubuntu.com/security/cis"
COMMON_CRITERIA_HOME_PAGE = "https://ubuntu.com/security/cc"
ESM_HOME_PAGE = "https://ubuntu.com/security/esm"
FIPS_HOME_PAGE = "https://ubuntu.com/security/fips"
LANDSCAPE_HOME_PAGE = "https://ubuntu.com/landscape"
LANDSCAPE_SAAS = "https://landscape.canonical.com"
LANDSCAPE_DOCS_INSTALL = "https://ubuntu.com/landscape/install"
LIVEPATCH_HOME_PAGE = "https://ubuntu.com/security/livepatch"
LIVEPATCH_SUPPORTED_KERNELS = (
    "https://ubuntu.com/security/livepatch/docs/kernels"
)
REALTIME_HOME_PAGE = "https://ubuntu.com/realtime-kernel"
ROS_HOME_PAGE = "https://ubuntu.com/robotics/ros-esm"
USG_DOCS = "https://ubuntu.com/security/certifications/docs/usg"

SECURITY_CVE_PAGE = "https://ubuntu.com/security/{cve}"

GCP_SERVICE_ACCOUNT_DOCS = (
    "https://cloud.google.com/iam/docs/service-account-overview"
)
