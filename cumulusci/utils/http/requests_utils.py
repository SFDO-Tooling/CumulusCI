import os
import subprocess
import sys
import typing as T
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

    - On all platforms, block `requests` from passing the `certifi` CA bundle
      to urllib3, so that urllib3 will instead set up an SSLContext by
      running SSLContext.load_default_certs()

    - On macOS, override SSLContext.load_default_certs() to load certs
      from the system keychain instead of from OpenSSL's default path.

    If a request explicitly sets `verify` to a path
    (perhaps via the REQUESTS_CA_BUNDLE environment variable),
    the CA certs from that path will still be trusted as well.

    The monkey-patching approach may be controversial, but it ensures that:
    a. we don't have to change every location we are using requests.get
       or requests.post without an explicit session
    b. our policy will also apply to 3rd-party libraries that use requests
    """
    if os.environ.get("CUMULUSCI_SYSTEM_CERTS") != "True":
        return
    global is_trust_patched
    if is_trust_patched:
        return
    is_trust_patched = True

    from requests.adapters import HTTPAdapter
    from requests.utils import DEFAULT_CA_BUNDLE_PATH

    # On macOS, monkey patch SSLContext.load_default_locations
    # to load CA certs from the system keychain
    if sys.platform == "darwin":
        import ssl

        cadata = get_macos_ca_certs()

        def load_default_certs(self, purpose=ssl.Purpose.SERVER_AUTH):
            self.load_verify_locations(cadata=cadata)

        ssl.SSLContext.load_default_certs = load_default_certs

    # On all platforms, monkey patch HTTPAdapter.cert_verify
    #  to avoid using the CA bundle from certifi

    orig_cert_verify = HTTPAdapter.cert_verify

    def cert_verify(self, conn, *args, **kw):
        orig_cert_verify(self, conn, *args, **kw)
        if conn.ca_certs == DEFAULT_CA_BUNDLE_PATH:
            conn.ca_certs = None

    HTTPAdapter.cert_verify = cert_verify


def get_certs_from_keychain(path: T.Optional[str] = None) -> str:
    """Get certs from the specified macOS keychain path (or default keychains if path is None)"""
    args = [
        "security",
        "find-certificate",
        "-a",
        "-p",
    ]
    if path:
        args.append(path)
    return subprocess.run(
        args,
        stdout=subprocess.PIPE,
        encoding="latin-1",
    ).stdout


def get_macos_ca_certs() -> str:
    """Get certs from both the default keychains and the SystemRootCertificates keychain"""
    return get_certs_from_keychain(None) + get_certs_from_keychain(
        "/System/Library/Keychains/SystemRootCertificates.keychain"
    )
