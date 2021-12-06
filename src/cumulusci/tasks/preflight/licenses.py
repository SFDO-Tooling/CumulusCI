from cumulusci.tasks.salesforce import BaseSalesforceApiTask


class GetAvailableLicenses(BaseSalesforceApiTask):
    def _run_task(self):
        self.return_values = [
            result["LicenseDefinitionKey"]
            for result in self.sf.query("SELECT LicenseDefinitionKey FROM UserLicense")[
                "records"
            ]
        ]
        licenses = "\n".join(self.return_values)
        self.logger.info(f"Found licenses:\n{licenses}")


class GetAvailablePermissionSetLicenses(BaseSalesforceApiTask):
    def _run_task(self):
        self.return_values = [
            result["PermissionSetLicenseKey"]
            for result in self.sf.query(
                "SELECT PermissionSetLicenseKey FROM PermissionSetLicense"
            )["records"]
        ]
        licenses = "\n".join(self.return_values)
        self.logger.info(f"Found permission set licenses:\n{licenses}")


class GetAvailablePermissionSets(BaseSalesforceApiTask):
    def _run_task(self):
        self.return_values = [
            result["Name"]
            for result in self.sf.query_all("SELECT Name FROM PermissionSet")["records"]
        ]
        permsets = "\n".join(self.return_values)
        self.logger.info(f"Found Permission Sets:\n{permsets}")
