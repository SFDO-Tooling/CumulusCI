import requests
from lxml import etree

from cumulusci.salesforce_api import mc_soap_envelopes as envelopes

from .base import BaseMarketingCloudTask


class MarketingCloudCreateSubscriberAttribute(BaseMarketingCloudTask):
    task_options = {
        "attribute_name": {
            "description": "The name of the Subscriber Attribute to deploy via the Marketing Cloud API.",
            "required": True,
        },
    }

    def _run_task(self):
        attribute_name = self.options["attribute_name"]
        # get soap envelope
        envelope = envelopes.CREATE_SUBSCRIBER_ATTRIBUTE
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
        status_code = root.find(
            ".//{http://exacttarget.com/wsdl/partnerAPI}StatusCode"
        ).text
        status_message = root.find(
            ".//{http://exacttarget.com/wsdl/partnerAPI}StatusMessage"
        ).text
        success = True
        if status_code == "OK":
            self.logger.info(
                f"Successfully created subscriber attribute: {attribute_name}."
            )
        if status_code != "OK":
            raise Exception(
                f"Error from Marketing Cloud: {status_message} \n\nFull response text: {response.text}"
            )
        self.return_values = {"success": success}
