import requests
from lxml import etree

from cumulusci.salesforce_api import mc_soap_envelopes as envelopes

from .base import BaseMarketingCloudTask


class CreateSubscriberAttribute(BaseMarketingCloudTask):
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


class CreateUser(BaseMarketingCloudTask):
    task_options = {
        "parent_bu_mid": {
            "description": "Specify the MID for Parent BU.",
            "required": True,
        },
        "default_bu_mid": {
            "description": "Set MID for BU to use as default (can be same as the parent).",
            "required": True,
        },
        "external_key": {
            "description": "Set the User's external key.",
            "required": False,
        },
        "user_name": {
            "description": "Set the User's name. Not the same as their username.",
            "required": False,
        },
        "user_email": {
            "description": "Set the User's email.",
            "required": True,
        },
        "user_password": {
            "description": "Set the User's password.",
            "required": True,
        },
        "user_username": {
            "description": "Set the User's username. Not the same as their name.",
            "required": True,
        },
        "role_id": {
            "description": "Assign a Role to the new User, specified as an ID. IDs for system defined roles located here: https://developer.salesforce.com/docs/atlas.en-us.noversion.mc-apis.meta/mc-apis/setting_user_permissions_via_the_web_services_api.htm",
            "required": False,
        },
    }

    def _run_task(self):
        # get soap envelope
        envelope = envelopes.CREATE_USER
        # fill the merge fields
        # check for optional parameters, construct xml nodes as required
        external_key = self.options.get("external_key", "")
        if external_key != "":
            external_key = f"<CustomerKey>{external_key}</CustomerKey>"

        user_name = self.options.get("user_name", "")
        if user_name != "":
            user_name = f"<Name>{user_name}</Name>"

        role_id = self.options.get("role_id", "")
        if role_id != "":
            role_id = f"<UserPermissions><ID>{role_id}</ID></UserPermissions>"

        envelope = envelope.format(
            soap_instance_url=self.mc_config.soap_instance_url,
            access_token=self.mc_config.access_token,
            parent_bu_mid=self.options.get("parent_bu_mid"),
            default_bu_mid=self.options.get("default_bu_mid"),
            external_key=external_key,
            user_name=user_name,
            user_email=self.options.get("user_email"),
            user_password=self.options.get("user_password"),
            user_username=self.options.get("user_username"),
            role_id=role_id,
        )
        # construct request
        # TO DO: DRY refactor
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
            user_username = self.options.get("user_username")
            self.logger.info(f"Successfully created User: {user_username}.")
        if status_code != "OK":
            raise Exception(
                f"Error from Marketing Cloud: {status_message}\n\nFull response text: {response.text}"
            )
        self.return_values = {"success": success}


class UpdateUserRole(BaseMarketingCloudTask):
    task_options = {
        "account_mid": {
            "description": "Specify the Account MID.",
            "required": True,
        },
        "external_key": {
            "description": "Specify the User's external key.",
            "required": False,
        },
        "user_name": {
            "description": "Specify the User's name. Not the same as their username.",
            "required": False,
        },
        "user_email": {
            "description": "Specify the User's email.",
            "required": True,
        },
        "user_password": {
            "description": "Specify the User's password.",
            "required": True,
        },
        "role_id": {
            "description": "Assign a Role to the User, specified as an ID. IDs for system defined roles located here: https://developer.salesforce.com/docs/atlas.en-us.noversion.mc-apis.meta/mc-apis/setting_user_permissions_via_the_web_services_api.htm",
            "required": True,
        },
    }

    def _run_task(self):
        # get soap envelope
        envelope = envelopes.UPDATE_USER_ROLE
        # fill the merge fields
        # check for optional parameters, construct xml nodes as required
        external_key = self.options.get("external_key", "")
        if external_key != "":
            external_key = f"<CustomerKey>{external_key}</CustomerKey>"

        user_name = self.options.get("user_name", "")
        if user_name != "":
            user_name = f"<Name>{user_name}</Name>"

        envelope = envelope.format(
            soap_instance_url=self.mc_config.soap_instance_url,
            access_token=self.mc_config.access_token,
            account_mid=self.options.get("account_mid"),
            external_key=external_key,
            user_name=user_name,
            user_email=self.options.get("user_email"),
            user_password=self.options.get("user_password"),
            role_id=self.options.get("role_id"),
        )
        # construct request
        # TO DO: DRY refactor
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
            user_name = self.options.get("user_name")
            self.logger.info(f"Successfully updated role for User: {user_name}.")
        if status_code != "OK":
            raise Exception(
                f"Error from Marketing Cloud: {status_message}\n\nFull response text: {response.text}"
            )
        self.return_values = {"success": success}
