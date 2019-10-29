import simple_salesforce
from cumulusci import __version__
from cumulusci.core.exceptions import ServiceNotConfigured, ServiceNotValid
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

CALL_OPTS_HEADER_KEY = "Sforce-Call-Options"


def get_simple_salesforce_connection(project_config, org_config, api_version=None):
    # Retry on long-running metadeploy jobs
    retries = Retry(total=5, status_forcelist=(502, 503, 504), backoff_factor=0.3)
    adapter = HTTPAdapter(max_retries=retries)

    sf = simple_salesforce.Salesforce(
        instance_url=org_config.instance_url,
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

    return sf
