import simple_salesforce

from cumulusci import __version__
from cumulusci.core.exceptions import ServiceNotConfigured
from cumulusci.core.exceptions import ServiceNotValid

CALL_OPTS_HEADER_KEY = "Sforce-Call-Options"


def get_simple_salesforce_connection(project_config, org_config, api_version=None):
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

    return sf
