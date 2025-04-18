from cumulusci.tasks.salesforce import BaseSalesforceApiTask


class BaseUserLicenseAwareTask(BaseSalesforceApiTask):
    def get_available_user_licenses(self, is_assignable=False):
        """Fetch active user licenses with availability."""
        query = "SELECT Id, LicenseDefinitionKey, TotalLicenses, UsedLicenses FROM UserLicense WHERE Status = 'Active'"
        return {
            lic["Id"]: lic
            for lic in self.sf.query(query)["records"]
            if not is_assignable or (lic["TotalLicenses"] > lic["UsedLicenses"])
        }

    def _log_list(self, title, items):
        self.logger.info(
            f"{title} ({len(items)}):\n" + "\n".join(f"- {item}" for item in items)
        )


class GetAvailableLicenses(BaseUserLicenseAwareTask):
    def _run_task(self):
        self.return_values = [
            result["LicenseDefinitionKey"]
            for result in self.get_available_user_licenses().values()
        ]
        licenses = "\n".join(self.return_values)
        self.logger.info(f"Found licenses:\n{licenses}")


class GetAssignableLicenses(BaseUserLicenseAwareTask):
    def _run_task(self):
        self.return_values = [
            result["LicenseDefinitionKey"]
            for result in self.get_available_user_licenses(is_assignable=True).values()
        ]
        licenses = "\n".join(self.return_values)
        self.logger.info(f"Found assignable licenses:\n{licenses}")


class GetAvailablePermissionSetLicenses(BaseSalesforceApiTask):
    def _run_task(self):
        query = "SELECT PermissionSetLicenseKey FROM PermissionSetLicense WHERE Status = 'Active'"
        self.return_values = [
            result["PermissionSetLicenseKey"]
            for result in self.sf.query(query)["records"]
        ]
        licenses = "\n".join(self.return_values)
        self.logger.info(f"Found permission set licenses:\n{licenses}")


class GetPermissionLicenseSetAssignments(BaseSalesforceApiTask):
    def _run_task(self):
        query = f"SELECT PermissionSetLicense.DeveloperName FROM PermissionSetLicenseAssign WHERE AssigneeId = '{self.org_config.user_id}'"
        self.return_values = [
            result["PermissionSetLicense"]["DeveloperName"]
            for result in self.sf.query_all(query)["records"]
        ]
        permsets = "\n".join(self.return_values)
        self.logger.info(f"Found permission licenses sets assigned:\n{permsets}")


class GetAvailablePermissionSets(BaseSalesforceApiTask):
    def _run_task(self):
        self.return_values = [
            result["Name"]
            for result in self.sf.query_all("SELECT Name FROM PermissionSet")["records"]
        ]
        permsets = "\n".join(self.return_values)
        self.logger.info(f"Found Permission Sets:\n{permsets}")


class GetAssignablePermissionSets(BaseUserLicenseAwareTask):
    def _run_task(self):
        license_data = self.get_available_user_licenses(is_assignable=True)
        permsets = self.sf.query_all("SELECT LicenseId, Name FROM PermissionSet")[
            "records"
        ]
        available_permsets = [
            ps["Name"]
            for ps in permsets
            if not ps["LicenseId"] or ps["LicenseId"] in license_data
        ]

        self.return_values = available_permsets
        permsets = "\n".join(self.return_values)
        self.logger.info(f"Found assignable permission sets:\n{permsets}")
