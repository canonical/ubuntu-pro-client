import datetime
import json
import logging
import os
import unicodedata
from typing import List, Optional

import apt_pkg

from uaclient import defaults, messages, system, util
from uaclient.api.u.pro.status.is_attached.v1 import _is_attached
from uaclient.apt import ensure_apt_pkg_init
from uaclient.clouds.identity import get_cloud_type
from uaclient.config import UAConfig
from uaclient.contract import ContractExpiryStatus, get_contract_expiry_status
from uaclient.data_types import (
    BoolDataValue,
    DataObject,
    DatetimeDataValue,
    Field,
    StringDataValue,
    data_list,
)
from uaclient.files import state_files

LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))


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


def do_selectors_apply(
    cfg: UAConfig, selectors: Optional[AptNewsMessageSelectors]
) -> bool:
    if selectors is None:
        return True

    if selectors.codenames is not None:
        if system.get_release_info().series not in selectors.codenames:
            return False

    if selectors.clouds is not None:
        cloud_id, fail = get_cloud_type()
        if fail is not None:
            return False
        if cloud_id not in selectors.clouds:
            return False

    if selectors.pro is not None:
        if selectors.pro != _is_attached(cfg).is_attached:
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
            LOG.debug("msg failed parsing: %r", e)
            continue
        if not is_message_valid(msg):
            LOG.debug("msg not valid: %r", msg)
            continue
        if not do_dates_apply(msg.begin, msg.end):
            LOG.debug("msg dates don't apply: %r", msg)
            continue
        if not do_selectors_apply(cfg, msg.selectors):
            LOG.debug("msg selectors don't apply: %r", msg)
            continue
        return msg
    return None


@ensure_apt_pkg_init
def fetch_aptnews_json(cfg: UAConfig):
    os.makedirs(defaults.UAC_RUN_PATH, exist_ok=True)
    acq = apt_pkg.Acquire()
    apt_news_file = apt_pkg.AcquireFile(
        acq, cfg.apt_news_url, hash="", destdir=defaults.UAC_RUN_PATH
    )
    acq.run()
    apt_news_contents = system.load_file(apt_news_file.destfile)
    return json.loads(
        apt_news_contents,
        cls=util.DatetimeAwareJSONDecoder,
    )


def fetch_and_process_apt_news(cfg: UAConfig) -> Optional[str]:
    news_dict = fetch_aptnews_json(cfg)
    msg = select_message(cfg, news_dict.get("messages", []))
    LOG.debug("using msg: %r", msg)
    if msg is not None:
        return "\n".join(msg.lines)
    return None


def local_apt_news(cfg: UAConfig) -> Optional[str]:
    """
    :return: str if local news, None otherwise
    """
    expiry_status, remaining_days = get_contract_expiry_status(cfg)

    if expiry_status == ContractExpiryStatus.ACTIVE_EXPIRED_SOON:
        return messages.CONTRACT_EXPIRES_SOON.pluralize(remaining_days).format(
            remaining_days=remaining_days
        )

    if expiry_status == ContractExpiryStatus.EXPIRED_GRACE_PERIOD:
        grace_period_remaining = (
            defaults.CONTRACT_EXPIRY_GRACE_PERIOD_DAYS + remaining_days
        )
        exp_dt = cfg.machine_token_file.contract_expiry_datetime
        if exp_dt is None:
            exp_dt_str = "Unknown"
        else:
            exp_dt_str = exp_dt.strftime("%d %b %Y")
        return messages.CONTRACT_EXPIRED_GRACE_PERIOD.pluralize(
            remaining_days
        ).format(
            expired_date=exp_dt_str, remaining_days=grace_period_remaining
        )

    if expiry_status == ContractExpiryStatus.EXPIRED:
        return messages.CONTRACT_EXPIRED

    return None


def format_news_for_apt_update(news: str) -> str:
    result = "#\n"
    for line in news.split("\n"):
        result += "# {}\n".format(line)
    result += "#\n"
    return result


def update_apt_news(cfg: UAConfig):
    try:
        news = local_apt_news(cfg)
        if not news:
            news = fetch_and_process_apt_news(cfg)
        if news:
            state_files.apt_news_raw_file.write(news)
            apt_update_formatted_news = format_news_for_apt_update(news)
            state_files.apt_news_contents_file.write(apt_update_formatted_news)
        else:
            state_files.apt_news_contents_file.delete()
            state_files.apt_news_raw_file.delete()
    except Exception as e:
        LOG.debug("something went wrong while processing apt_news: %r", e)
        state_files.apt_news_contents_file.delete()
        state_files.apt_news_raw_file.delete()
