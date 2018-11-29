import json
import logging
import six


class UrlError(IOError):

    def __init__(self, cause, code=None, headers=None, url=None):
        super(UrlError, self).__init__(str(cause))
        self.cause = cause
        self.code = code
        self.headers = headers
        if self.headers is None:
            self.headers = {}
        self.url = url


def decode_binary(blob, encoding='utf-8'):
    """Convert a binary type into a text type using given encoding."""
    if isinstance(blob, six.string_types):
        return blob
    return blob.decode(encoding)


def encode_text(text, encoding='utf-8'):
    """Convert a text string into a binary type using given encoding."""
    if isinstance(text, six.binary_type):
        return text
    return text.encode(encoding)


def load_file(filename, decode=True):
    """Read filename and decode content."""
    with open(filename, 'rb') as stream:
        content = stream.read()
    if decode:
        return decode_binary(content)
    return content


def maybe_parse_json(content):
    """Attempt to parse json content.

    @return: Structured content on success and None on failure.
    """
    try:
        return json.loads(content)
    except ValueError:
        return None


def readurl(url, data=None, headers=None, quiet=False):
    req = six.moves.urllib.request.Request(url, data=data, headers=headers)
    if not quiet:
        logging.debug(
            'Reading url: %s, headers: %s, data: %s', url, headers, data)
    resp = six.moves.urllib.request.urlopen(req)
    content = decode_binary(resp.read())
    if 'application/json' in resp.headers.get('Content-type', ''):
        content = json.loads(content)
    return content


def write_file(filename, content, omode='wb'):
    """Write content to the provided filename encoding it if necessary."""
    if 'b' in omode.lower():
        content = encode_text(content)
    else:
        content = decode_binary(content)
    with open(filename, omode) as fh:
        fh.write(content)
        fh.flush()

