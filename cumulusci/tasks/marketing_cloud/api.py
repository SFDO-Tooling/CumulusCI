import requests
from lxml import etree

from cumulusci.salesforce_api import mc_soap_envelopes as envelopes

from .base import BaseMarketingCloudTask


class MarketingCloudDeploySubscriberAttribute(BaseMarketingCloudTask):
    task_options = {
        "attribute_name": {
            "description": "The name of the Subscriber Attribute to deploy via the Marketing Cloud API.",
            "required": True,
        },
    }

    def _run_task(self):
        attribute_name = self.options["attribute_name"]
        # get soap envelope
        envelope = envelopes.SUBSCRIBER_ATTRIBUTE_DEPLOY
        # fill the merge fields
        envelope = envelope.format(
            soap_instance_url=self.mc_config.soap_instance_url,
            access_token=self.mc_config.access_token,
            attribute_name=attribute_name,
        )
        # construct request
        response = requests.post(
            f"{self.mc_config.soap_instance_url}Service.asmx",
            data=envelope.encode("utf-8"),
            headers={"Content-Type": "text/xml; charset=utf-8"},
        )
        response.raise_for_status()
        # check resulting status code
        root = etree.fromstring(response.content)
        status = root.find(".//{http://exacttarget.com/wsdl/partnerAPI}StatusCode").text
        success = True
        if status == "OK":
            self.logger.info(
                f"Successfully deployed subscriber attribute: {attribute_name}."
            )
        if status != "OK":
            raise Exception(f"Error from Marketing Cloud: {response.text}")
        self.return_values = {"success": success}
