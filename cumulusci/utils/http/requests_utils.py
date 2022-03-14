# import os
import sys
from json import JSONDecodeError

from cumulusci.core.exceptions import CumulusCIException


def safe_json_from_response(response):
    "Check JSON response is HTTP200 and actually JSON."
    response.raise_for_status()

    try:
        return response.json()
    except JSONDecodeError:
        raise CumulusCIException(f"Cannot decode as JSON:  {response.text}")


is_trust_patched = False


def init_requests_trust():
    """Monkey-patch requests to ensure we validate certificates using the preferred trust store.

    Currently this does nothing unless the CUMULUSCI_SYSTEM_CERTS environment variable is set to True.
    (That may change so that this is done by default, after further testing.)

    This is called from cumulusci.__init__ to enact our policy:

    - If a request explicitly sets `verify` to a path
      (perhaps via the REQUESTS_CA_BUNDLE environment variable),
      we'll continue to honor that.

    - On macOS, verify certificates via the SecureTransport API,
      which is aware of the system keychain.

    - On other platforms, verify certificates using urllib3's default approach,
      which loads CAs using SSLContext.load_default_certs()
      and should work on Linux and Windows in most cases.

    The monkey-patching approach may be controversial, but it ensures that:
    a. we don't have to change every location we are using requests.get or requests.post without an explicit session
    b. our policy will also apply to 3rd-party libraries that use requests
    """
    # if os.environ.get("CUMULUSCI_SYSTEM_CERTS") != "True":
    #     return
    global is_trust_patched
    if is_trust_patched:
        return

    # On macOS, replace urllib3's SSLContext with one that uses SecureTransport
    if sys.platform == "darwin":
        import urllib3.contrib.securetransport

        urllib3.contrib.securetransport.inject_into_urllib3()

    # Monkey patch HTTPAdapter.cert_verify to avoid using the CA bundle from certifi
    from requests.adapters import HTTPAdapter
    from requests.utils import DEFAULT_CA_BUNDLE_PATH

    orig_cert_verify = HTTPAdapter.cert_verify

    def cert_verify(self, conn, *args, **kw):
        orig_cert_verify(self, conn, *args, **kw)
        if conn.ca_certs == DEFAULT_CA_BUNDLE_PATH:
            conn.ca_certs = None

    HTTPAdapter.cert_verify = cert_verify
