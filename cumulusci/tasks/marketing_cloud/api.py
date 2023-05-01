import requests

from cumulusci.core.utils import process_bool_arg
from cumulusci.salesforce_api import mc_soap_envelopes as envelopes

from .base import BaseMarketingCloudTask


class CreateSubscriberAttribute(BaseMarketingCloudTask):
    task_options = {  # TODO: should use `class Options instead`
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
        response = requests.post(
            f"{self.mc_config.soap_instance_url}Service.asmx",
            data=envelope.encode("utf-8"),
            headers={"Content-Type": "text/xml; charset=utf-8"},
        )
        self._check_soap_response(response)
        self.logger.info(
            f"Successfully created subscriber attribute: {attribute_name}."
        )
        self.return_values = {"success": True}


class CreateUser(BaseMarketingCloudTask):
    task_options = {  # TODO: should use `class Options instead`
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
            "sensitive": True,
        },
        "user_username": {
            "description": "Set the User's username. Not the same as their name.",
            "required": True,
        },
        "role_id": {
            "description": "Assign a Role to the new User, specified as an ID. IDs for system defined roles located here: https://developer.salesforce.com/docs/atlas.en-us.noversion.mc-apis.meta/mc-apis/setting_user_permissions_via_the_web_services_api.htm",
            "required": False,
        },
        "activate_if_existing": {
            "description": "Activate the user if it already exists in an inactive state. Default: False",
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

        user_username = self.options.get("user_username")

        user_name = self.options.get("user_name", "")
        if user_name != "":
            user_name = f"<Name>{user_name}</Name>"

        role_id = self.options.get("role_id", "")
        if role_id != "":
            role_id = f"<UserPermissions><ID>{role_id}</ID></UserPermissions>"

        active_flag = (
            "<ActiveFlag>true</ActiveFlag>"
            if process_bool_arg(self.options.get("activate_if_existing"))
            else ""
        )

        envelope = envelope.format(
            soap_instance_url=self.mc_config.soap_instance_url,
            access_token=self.mc_config.access_token,
            parent_bu_mid=self.options.get("parent_bu_mid"),
            default_bu_mid=self.options.get("default_bu_mid"),
            external_key=external_key,
            user_name=user_name,
            user_email=self.options.get("user_email"),
            user_password=self.options.get("user_password"),
            user_username=user_username,
            role_id=role_id,
            active_flag=active_flag,
        )
        response = requests.post(
            f"{self.mc_config.soap_instance_url}Service.asmx",
            data=envelope.encode("utf-8"),
            headers={"Content-Type": "text/xml; charset=utf-8"},
        )
        self._check_soap_response(response)
        self.logger.info(f"Successfully created User: {user_username}.")
        self.return_values = {"success": True}


class UpdateUserRole(BaseMarketingCloudTask):
    task_options = {  # TODO: should use `class Options instead`
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
            "sensitive": True,
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
        response = requests.post(
            f"{self.mc_config.soap_instance_url}Service.asmx",
            data=envelope.encode("utf-8"),
            headers={"Content-Type": "text/xml; charset=utf-8"},
        )
        self._check_soap_response(response)
        user_name = self.options.get("user_name")
        self.logger.info(f"Successfully updated role for User: {user_name}.")
        self.return_values = {"success": True}
