from cumulusci.core.tasks import BaseTask
from cumulusci.tasks.marketing_cloud.util import get_mc_user_info
from cumulusci.utils.xml import lxml_parse_string


class BaseMarketingCloudTask(BaseTask):
    """Base task for interacting with Marketing Cloud

    For API calls to a MC tenant, you can get a fresh
    access token via the marketing cloud config like so:

    self.mc_config.access_token
    """

    salesforce_task = False

    def _init_task(self):
        super()._init_task()
        self.mc_config = self.project_config.keychain.get_service("marketing_cloud")
        self.mc_oauth2_client_config = self.project_config.keychain.get_service(
            "oauth2_client", self.mc_config.oauth2_client
        )

    def _check_soap_response(self, response):
        """Make sure the response indicates success."""
        response.raise_for_status()
        root = lxml_parse_string(response.content)
        status_code = root.find(
            ".//{http://exacttarget.com/wsdl/partnerAPI}StatusCode"
        ).text
        status_message = root.find(
            ".//{http://exacttarget.com/wsdl/partnerAPI}StatusMessage"
        ).text
        if status_code != "OK":
            raise Exception(
                f"Error from Marketing Cloud: {status_message}\n\nFull response text: {response.text}"
            )

    def get_mc_stack_key(self) -> str:
        """Return the stack_key associated with this tasks's marketing_cloud service"""
        user_info_payload = get_mc_user_info(
            self.mc_oauth2_client_config, self.mc_config
        )
        return user_info_payload["organization"]["stack_key"]
