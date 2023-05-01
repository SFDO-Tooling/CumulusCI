from urllib.parse import urlparse

import simple_salesforce
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from cumulusci import __version__
from cumulusci.core.exceptions import ServiceNotConfigured, ServiceNotValid

CALL_OPTS_HEADER_KEY = "Sforce-Call-Options"


def get_simple_salesforce_connection(
    project_config, org_config, api_version=None, base_url: str = None
):

    # Retry on long-running metadeploy jobs
    retries = Retry(total=5, status_forcelist=(502, 503, 504), backoff_factor=0.3)
    adapter = HTTPAdapter(max_retries=retries)
    instance = org_config.instance_url

    # Attempt to get the host and port from the URL
    instance_url = urlparse(org_config.instance_url)
    instance = instance_url.hostname
    port = instance_url.port

    if port:
        instance = f"{instance}:{port}"

    sf = simple_salesforce.Salesforce(
        instance=instance,
        session_id=org_config.access_token,
        version=api_version or project_config.project__package__api_version,
    )
    try:
        app = project_config.keychain.get_service("connectedapp")
        client_name = app.client_id
    except (ServiceNotValid, ServiceNotConfigured):
        client_name = "CumulusCI/{}".format(__version__)

    sf.headers.setdefault(CALL_OPTS_HEADER_KEY, "client={}".format(client_name))
    sf.session.mount("http://", adapter)
    sf.session.mount("https://", adapter)

    if base_url:
        base_url = (
            base_url.strip("/") + "/"
        )  # exactly one training slash and no leading slashes
        sf.base_url += base_url

    return sf
