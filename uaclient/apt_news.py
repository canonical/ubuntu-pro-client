import datetime
import json
import logging
import os
import unicodedata
from typing import List, Optional

import apt_pkg

from uaclient import defaults, messages, system, util
from uaclient.clouds.identity import get_cloud_type
from uaclient.config import UAConfig
from uaclient.data_types import (
    BoolDataValue,
    DataObject,
    DatetimeDataValue,
    Field,
    StringDataValue,
    data_list,
)
from uaclient.files import state_files
from uaclient.jobs.update_messaging import (
    ContractExpiryStatus,
    get_contract_expiry_status,
)


class AptNewsMessageSelectors(DataObject):
    fields = [
        Field("codenames", data_list(StringDataValue), required=False),
        Field("clouds", data_list(StringDataValue), required=False),
        Field("pro", BoolDataValue, required=False),
    ]

    def __init__(
        self,
        *,
        codenames: Optional[List[str]] = None,
        clouds: Optional[List[str]] = None,
        pro: Optional[bool] = None
    ):
        self.codenames = codenames
        self.clouds = clouds
        self.pro = pro


class AptNewsMessage(DataObject):
    fields = [
        Field("begin", DatetimeDataValue),
        Field("end", DatetimeDataValue, required=False),
        Field("selectors", AptNewsMessageSelectors, required=False),
        Field("lines", data_list(StringDataValue)),
    ]

    def __init__(
        self,
        *,
        begin: datetime.datetime,
        end: Optional[datetime.datetime] = None,
        selectors: Optional[AptNewsMessageSelectors] = None,
        lines: List[str]
    ):
        self.begin = begin
        self.end = end
        self.selectors = selectors
        self.lines = lines


def format_message(msg: AptNewsMessage) -> str:
    result = "#\n"
    for line in msg.lines:
        result += "# {}\n".format(line)
    result += "#\n"
    return result


def do_selectors_apply(
    cfg: UAConfig, selectors: Optional[AptNewsMessageSelectors]
) -> bool:
    if selectors is None:
        return True

    if selectors.codenames is not None:
        if system.get_platform_info()["series"] not in selectors.codenames:
            return False

    if selectors.clouds is not None:
        cloud_id, fail = get_cloud_type()
        if fail is not None:
            return False
        if cloud_id not in selectors.clouds:
            return False

    if selectors.pro is not None:
        if selectors.pro != cfg.is_attached:
            return False

    return True


def do_dates_apply(
    begin: datetime.datetime, end: Optional[datetime.datetime]
) -> bool:
    now = datetime.datetime.now(datetime.timezone.utc)
    if now < begin:
        return False

    one_month_after_begin = begin + datetime.timedelta(days=30)
    if end is None or end > one_month_after_begin:
        end_to_use = one_month_after_begin
    else:
        end_to_use = end
    if now > end_to_use:
        return False

    return True


def is_control_char(c: str) -> bool:
    return unicodedata.category(c)[0] == "C"


def is_message_valid(msg: AptNewsMessage) -> bool:
    if len(msg.lines) < 1:
        return False
    if len(msg.lines) > 3:
        return False

    for line in msg.lines:
        if any([is_control_char(c) for c in line]):
            return False
        if len(line) > 77:
            return False

    return True


def select_message(
    cfg: UAConfig, messages: List[dict]
) -> Optional[AptNewsMessage]:
    for msg_dict in messages:
        try:
            msg = AptNewsMessage.from_dict(msg_dict)
        except Exception as e:
            logging.debug("msg failed parsing: %r", e)
            continue
        if not is_message_valid(msg):
            logging.debug("msg not valid: %r", msg)
            continue
        if not do_dates_apply(msg.begin, msg.end):
            logging.debug("msg dates don't apply: %r", msg)
            continue
        if not do_selectors_apply(cfg, msg.selectors):
            logging.debug("msg selectors don't apply: %r", msg)
            continue
        return msg
    return None


def fetch_aptnews_json(cfg: UAConfig):
    os.makedirs(defaults.UAC_RUN_PATH, exist_ok=True)
    acq = apt_pkg.Acquire()
    apt_news_file = apt_pkg.AcquireFile(
        acq, cfg.apt_news_url, destdir=defaults.UAC_RUN_PATH
    )
    acq.run()
    apt_news_contents = system.load_file(apt_news_file.destfile)
    return json.loads(
        apt_news_contents,
        cls=util.DatetimeAwareJSONDecoder,
    )


def fetch_and_process_apt_news(cfg: UAConfig):
    try:
        news_dict = fetch_aptnews_json(cfg)
        msg = select_message(cfg, news_dict.get("messages", []))
        logging.debug("using msg: %r", msg)
        if msg is not None:
            msg_str = format_message(msg)
            state_files.apt_news_contents_file.write(msg_str)
        else:
            state_files.apt_news_contents_file.delete()
    except Exception as e:
        logging.debug("something went wrong while processing apt_news: %r", e)
        state_files.apt_news_contents_file.delete()


def local_apt_news(cfg: UAConfig) -> bool:
    """
    :return: True if local news was written, False otherwise
    """
    expiry_status, remaining_days = get_contract_expiry_status(cfg)

    if expiry_status == ContractExpiryStatus.ACTIVE_EXPIRED_SOON:
        state_files.apt_news_contents_file.write(
            messages.CONTRACT_EXPIRES_SOON_APT_NEWS.format(
                remaining_days=remaining_days
            )
        )
        return True

    if expiry_status == ContractExpiryStatus.EXPIRED_GRACE_PERIOD:
        grace_period_remaining = (
            defaults.CONTRACT_EXPIRY_GRACE_PERIOD_DAYS + remaining_days
        )
        exp_dt = cfg.machine_token_file.contract_expiry_datetime
        if exp_dt is None:
            exp_dt_str = "Unknown"
        else:
            exp_dt_str = exp_dt.strftime("%d %b %Y")
        state_files.apt_news_contents_file.write(
            messages.CONTRACT_EXPIRED_GRACE_PERIOD_APT_NEWS.format(
                expired_date=exp_dt_str, remaining_days=grace_period_remaining
            )
        )
        return True

    if expiry_status == ContractExpiryStatus.EXPIRED:
        state_files.apt_news_contents_file.write(
            messages.CONTRACT_EXPIRED_APT_NEWS
        )
        return True

    return False


def update_apt_news(cfg: UAConfig):
    local_news_written = local_apt_news(cfg)
    if not local_news_written:
        apt_pkg.init()
        fetch_and_process_apt_news(cfg)
