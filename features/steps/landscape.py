import hmac
import json
import time
from base64 import b64encode
from hashlib import sha256
from urllib.parse import quote
from urllib.request import Request, urlopen

from behave import step


def _landscape_api_request(access_key, secret_key, action, action_params):
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    params = {
        "action": action,
        "access_key_id": access_key,
        "signature_method": "HmacSHA256",
        "signature_version": "2",
        "timestamp": timestamp,
        "version": "2011-08-01",
        **action_params,
    }
    method = "POST"
    uri = "https://landscape.canonical.com/api/"
    host = "landscape.canonical.com"
    path = "/api/"

    formatted_params = "&".join(
        quote(k, safe="~") + "=" + quote(v, safe="~")
        for k, v in sorted(params.items())
    )

    to_sign = "{method}\n{host}\n{path}\n{formatted_params}".format(
        method=method,
        host=host,
        path=path,
        formatted_params=formatted_params,
    )
    digest = hmac.new(secret_key.encode(), to_sign.encode(), sha256).digest()
    signature = b64encode(digest)
    formatted_params += "&signature=" + quote(signature)

    request = Request(
        uri,
        headers={"Host": host},
        method=method,
        data=formatted_params.encode(),
    )
    response = urlopen(request)

    return response.code, json.load(response)


@step("I reject all pending computers on Landscape")
def reject_all_pending_computers(context):
    access_key = context.pro_config.landscape_api_access_key
    secret_key = context.pro_config.landscape_api_secret_key
    code, pending_computers = _landscape_api_request(
        access_key, secret_key, "GetPendingComputers", {}
    )
    assert code == 200
    reject_params = {
        "computer_ids.{}".format(i + 1): str(computer["id"])
        for i, computer in enumerate(pending_computers)
    }
    code, _resp = _landscape_api_request(
        access_key, secret_key, "RejectPendingComputers", reject_params
    )
    assert code == 200
