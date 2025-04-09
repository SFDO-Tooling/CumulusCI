from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
from azure.devops.exceptions import AzureDevOpsAuthenticationError

import logging
logger = logging.getLogger(__name__)

def validate_service(options: dict, keychain) -> dict:
    personal_access_token = options["token"]
    organization_url = options["organization_url"]
    
    services = keychain.get_services_for_type("azure_devops")
    if services:
        hosts = [service.organization_url for service in services]
        if hosts.count(organization_url) > 1:
            raise AzureDevOpsAuthenticationError(
                f"More than one Azure Devops service configured for domain {organization_url}."
            )
    
    try:
        # Get a client (the "core" client provides access to projects, teams, etc)
        connection = _authenticate(personal_access_token, organization_url)
        core_client = connection.clients.get_core_client()
        base_url = core_client.config.base_url
        assert organization_url in base_url, f"https://{organization_url}"
    except AttributeError as e:
        raise AzureDevOpsAuthenticationError(
            f"Authentication Error. ({str(e)})"
        )
    except Exception as e:
        raise AzureDevOpsAuthenticationError(
            f"Authentication Error. ({str(e)})"
        )

    return options

def _authenticate(token: str, org_url: str):
    organization_url = f"https://{org_url}"
    # Create a connection to the org
    credentials = BasicAuthentication('', token)
    connection = Connection(base_url=organization_url, creds=credentials)
    
    # Get a client (the "core" client provides access to projects, teams, etc)
    connection.authenticate()
    
    return connection

def get_azure_api_conntection(service_config, session=None):
    return _authenticate(service_config.token, service_config.organization_url)
