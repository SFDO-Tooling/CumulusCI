import pathlib

import yaml

from cumulusci.core.exceptions import CumulusCIException, TaskOptionsError
from cumulusci.tasks.salesforce.BaseSalesforceApiTask import BaseSalesforceApiTask


class LoadCustomSettings(BaseSalesforceApiTask):
    """Load Custom Settings (both List and Hierarchy) into an org
     from a YAML-format settings file.

     Each top-level YAML key should be the API name of a Custom Setting.
     List Custom Settings should contain a nested map of names to values.
     Hierarchy Custom settings should contain a list, each of which contains
     a ``data`` key and a ``location`` key. The ``location`` key may contain either
     ``profile: <profile name>``, ``user: name: <username>``, ``user: email: <email>``,
     or ``org``. Example:

    .. code-block:: yaml

         List__c:
             Test:
                 MyField__c: 1
             Test 2:
                 MyField__c: 2
         Hierarchy__c:
             -
                 location: org
                 data:
                     MyField__c: 1
             -
                 location:
                     user:
                         name: test@example.com
                 data:
                     MyField__c: 2
    """

    task_options = {
        "settings_path": {
            "description": "The path to a YAML settings file",
            "required": True,
        }
    }

    def _run_task(self):
        path = pathlib.Path(self.options["settings_path"])
        if not path.is_file():
            raise TaskOptionsError(f"File {path} does not exist")

        with path.open("r") as f:
            self.settings = yaml.safe_load(f)

        self.logger.info("Starting Custom Settings load")
        self._load_settings()
        self.logger.info("Finished Custom Settings load")

    def _load_settings(self):
        # For each top-level heading in our YAML doc, create one or more
        # custom settings.

        for custom_setting, settings_data in self.settings.items():
            proxy_obj = getattr(self.sf, custom_setting)
            # If this level is a dict, we're working with a List Custom Setting
            # If it's a list, we have a Hierarchy Custom Setting.
            if isinstance(settings_data, dict):
                for setting_instance, instance_data in settings_data.items():
                    self.logger.info(
                        f"Loading List Custom Setting {custom_setting}.{setting_instance}"
                    )
                    proxy_obj.upsert("Name/{}".format(setting_instance), instance_data)
            elif isinstance(settings_data, list):
                for setting_instance in settings_data:
                    query = None

                    if "location" in setting_instance:
                        if "profile" in setting_instance["location"]:
                            # Query for a matching Profile to assign the Setup Owner Id.
                            profile_name = setting_instance["location"]["profile"]
                            query = (
                                f"SELECT Id FROM Profile WHERE Name = '{profile_name}'"
                            )
                        elif "user" in setting_instance["location"]:
                            if "name" in setting_instance["location"]["user"]:
                                # Query for a matching User to assign the Setup Owner Id.
                                user_name = setting_instance["location"]["user"]["name"]
                                query = f"SELECT Id FROM User WHERE Username = '{user_name}'"
                            elif "email" in setting_instance["location"]["user"]:
                                # Query for a matching User to assign the Setup Owner Id.
                                email_address = setting_instance["location"]["user"][
                                    "email"
                                ]
                                query = f"SELECT Id FROM User WHERE Email = '{email_address}'"
                        elif "org" == setting_instance["location"]:
                            # Assign the Setup Owner Id to the organization.
                            query = "SELECT Id FROM Organization"

                    if query is None:
                        raise CumulusCIException(
                            f"No valid Setup Owner assignment found for Custom Setting {custom_setting}. Add a `location:` key."
                        )

                    matches = self.sf.query(query)
                    if matches["totalSize"] != 1:
                        raise CumulusCIException(
                            f"{matches['totalSize']} records matched the settings location query {query}. Exactly one result is required."
                        )

                    setup_owner_id = matches["records"][0]["Id"]

                    # We can't upsert on SetupOwnerId. Query for any existing records.
                    existing_records = self.sf.query(
                        f"SELECT Id FROM {custom_setting} WHERE SetupOwnerId = '{setup_owner_id}'"
                    )

                    setting_instance["data"].update({"SetupOwnerId": setup_owner_id})
                    if existing_records["totalSize"] == 0:
                        self.logger.info(
                            f"Loading Hierarchy Custom Setting {custom_setting} with owner id {setup_owner_id}"
                        )
                        proxy_obj.create(setting_instance["data"])
                    else:
                        self.logger.info(
                            f"Updating Hierarchy Custom Setting {custom_setting} with owner id {setup_owner_id}"
                        )
                        proxy_obj.update(
                            existing_records["records"][0]["Id"],
                            setting_instance["data"],
                        )
            else:
                raise CumulusCIException(
                    "Each Custom Settings entry must be a list or a map structure."
                )
