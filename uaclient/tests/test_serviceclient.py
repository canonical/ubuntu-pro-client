import mock
from urllib.error import HTTPError
from io import BytesIO

import pytest

from uaclient import util
from uaclient.serviceclient import UAServiceClient


class OurServiceClientException(Exception):

    def __init__(self, exc, details):
        self.exc = exc
        self.details = details


class OurServiceClient(UAServiceClient):

    @property
    def api_error_cls(self):
        return OurServiceClientException

    @property
    def cfg_url_base_attr(self):
        return 'unused'


class TestRequestUrl:

    # TODO: Non error-path tests

    @pytest.mark.parametrize('fp,expected_exception,expected_attrs', (
        (BytesIO(), util.UrlError, {'code': 619}),
        (BytesIO(b'{"a": "b"}'), OurServiceClientException,
         {'details': {"a": "b"}}),
    ))
    @mock.patch('uaclient.serviceclient.util.readurl')
    def test_urlerror_with_read(
            self, m_readurl, fp, expected_exception, expected_attrs):
        m_readurl.side_effect = HTTPError(None, 619, None, None, fp)

        client = OurServiceClient(cfg=mock.MagicMock())
        with pytest.raises(expected_exception) as excinfo:
            client.request_url('/')

        for attr, expected_value in expected_attrs.items():
            assert expected_value == getattr(excinfo.value, attr)
