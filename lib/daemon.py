import datetime
import logging
import sys
import threading

from uaclient import util
from uaclient.cli import setup_logging
from uaclient.clouds.identity import get_cloud_type


def gcp_auto_attach():
    # just a for loop in case I mess up, it'll only do whatever mistake 100 times
    for _i in range(100):
        now = datetime.datetime.now()
        logging.info("Requesting metadata at {}".format(now))
        try:
            result = util.readurl(
                "http://metadata.google.internal/computeMetadata/v1/instance/attributes/?recursive=true&wait_for_change=true",
                headers={"Metadata-Flavor": "Google"},
            )
            logging.info(result)
        except Exception as e:
            logging.exception(e)


def main():
    cloud, _none_reason = get_cloud_type()
    threads = []
    if cloud == "gce":
        thread = threading.Thread(target=gcp_auto_attach)
        thread.start()
        threads.append(thread)

    # maybe do other stuff in other threads one day

    for thread in threads:
        thread.join()

    return 0


if __name__ == "__main__":
    setup_logging(logging.DEBUG, logging.DEBUG)
    sys.exit(main())
