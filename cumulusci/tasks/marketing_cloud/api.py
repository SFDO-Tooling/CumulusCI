import requests

from cumulusci.salesforce_api import mc_soap_envelopes as envelopes

from .base import BaseMarketingCloudTask

MC_API_ENDPOINT = "https://{tssd}.soap.marketingcloudapis.com/Service.asmx"


class MarketingCloudDeploySubscriberAttribute(BaseMarketingCloudTask):
    task_options = {
        "attribute_name": {
            "description": "The name of the Subscriber Attribute to deploy via the Marketing Cloud API.",
            "required": True,
        },
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)

    def _run_task(self):
        attribute_name = self.options.get("attribute_name")
        # get soap envelope
        envelope = envelopes.SUBSCRIBER_ATTRIBUTE_DEPLOY
        # fill the merge fields
        envelope.format(
            soap_instance_url=self.mc_config.soap_instance_url,
            access_token=self.mc_config.access_token,
            attribute_name=attribute_name,
        )
        # construct request
        headers = {
            "Content-Type": "text/xml",
            "charset": "utf-8",
            "SOAPAction": "Create",
        }

        response = requests.post(
            f"{self.mc_config.soap_instance_url}Service.asmx",
            data=envelope,
            headers=headers,
        )
        print(response.status_code, response.text)
        # send request
        # handle request callbacks?
