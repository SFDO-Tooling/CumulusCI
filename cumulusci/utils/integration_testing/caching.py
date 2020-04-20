from tempfile import gettempdir
from pathlib import Path
import responses
import re
import requests
import json
import logging


from contextlib import contextmanager


# We don't use a standard HTTP caching library because we want to cache
# things that Salesforce would consider uncacheable.


def simple_tempdir():
    """Try to find a simple tempfile directory instead of the weird ones MacOS puts in $TEMPDIR"""
    for p in ["/tmp", "/var/tmp", "/usr/tmp", "C:\\TEMP", "C:\\TMP", "\\TEMP", "\\TMP"]:
        path = Path(p)
        if Path.exists(path):
            return path

    return Path(gettempdir())


def get_valid_filename(s):
    """
    Return the given string converted to a string that can be used for a clean
    filename. Remove leading and trailing spaces; convert other spaces to
    underscores; and remove anything that is not an alphanumeric, dash,
    underscore, or dot.
    >>> get_valid_filename("john's portrait in 2004.jpg")
    'johns_portrait_in_2004.jpg'

    From https://github.com/django/django/blob/master/django/utils/text.py#L222
    """
    s = str(s).strip().replace(" ", "_").replace(":", ".").replace("/", "-")
    return re.sub(r"(?u)[^-\w.]", "", s)


class RequestCache:
    def __init__(self):
        parent_tempdir = simple_tempdir()
        self.tempdir = parent_tempdir / "cumulusci_testing_cache"

        self.tempdir.mkdir(exist_ok=True)
        self.rsps = responses.RequestsMock(assert_all_requests_are_fired=False)
        self.rsps.add_callback(
            responses.GET, re.compile(".*"), callback=self.request_callback
        )
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("Using cache instead of real HTTP calls")

    def start(self):
        self.rsps.start()

    def stop(self):
        self.rsps.stop()

    def request_callback(self, request):
        self.rsps.stop()
        response_tuple = self.cached_request(request)
        self.rsps.start()
        return response_tuple

    def cached_request(self, request):
        filename = self.tempdir / get_valid_filename(request.url)
        try:
            response_tuple = self.read_response(filename)
            self.logger.info(f"Read from cache: {request.url}")
        except (FileNotFoundError, json.JSONDecodeError):
            self.logger.info(f"Cache miss: {request.url}")
            response = requests.request(
                request.method, request.url, headers=request.headers, data=request.body
            )
            if response.status_code != 200:
                self.logger.info(f"Non-200 Response: {request.url}")
                return response.status_code, response.headers, response.content
            self.write_response(filename, response)
            response_tuple = self.read_response(filename)
        return response_tuple

    def write_response(self, base_filename, response):
        try:
            with open(str(base_filename) + ".headers.json", "w", encoding="utf-8") as f:
                headers = dict(response.headers)
                if headers.get("Content-Encoding"):
                    del headers["Content-Encoding"]
                json.dump(headers, f)

            with open(str(base_filename) + ".body.json", "wb") as f:
                for chunk in response.iter_content(chunk_size=128):
                    f.write(chunk)
        except Exception as e:
            self.logger.warning(f"Exception caught. Removing cache: {e}")
            base_filename.remove()
            raise e

    def read_response(self, base_filename):
        with open(str(base_filename) + ".headers.json", "r", encoding="utf-8") as f:
            headers = json.load(f)

        with open(str(base_filename) + ".body.json", "rb") as f:
            body = f.read()

        return 200, headers, body


@contextmanager
def caching_proxy(enable=True):
    if enable:
        cache = RequestCache()
        cache.start()
    else:
        cache = None
    yield cache
    if cache:
        cache.stop()
