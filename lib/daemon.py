import asyncio
import concurrent.futures
import datetime
import logging
import sys

from uaclient import util
from uaclient.cli import setup_logging
from uaclient.clouds.identity import get_cloud_type


async def run_in_thread(fn, *args):
    return asyncio.get_event_loop().run_in_executor(None, fn, *args)


async def gcp_auto_attach():
    # just a for loop in case I mess up, it'll only do whatever mistake 100 times
    for _i in range(100):
        now = datetime.datetime.now()
        logging.info("Requesting metadata at {}".format(now))
        try:
            result = await run_in_thread(
                util.readurl,
                "http://metadata.google.internal/computeMetadata/v1/instance/attributes/?recursive=true&wait_for_change=true",
                headers={"Metadata-Flavor": "Google"},
            )
            logging.info(result)
        except Exception as e:
            logging.exception(e)


async def main():
    cloud, _none_reason = get_cloud_type()
    coroutines = []
    if cloud == "gce":
        coroutines.append(gcp_auto_attach())

    await asyncio.gather(*coroutines)


if __name__ == "__main__":
    setup_logging(logging.DEBUG, logging.DEBUG)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
