from cumulusci.tasks.salesforce import BaseSalesforceApiTask


class DisplayFiles(BaseSalesforceApiTask):
    task_docs = """
    Lists the available documents that has been uploaded to a library in Salesforce CRM Content or Salesforce Files
    """

    def _run_task(self):
        self.return_values = [
            {
                "Id": result["Id"],
                "FileName": result["Title"],
                "FileType": result["FileType"],
            }
            for result in self.sf.query(
                "SELECT Title, Id, FileType FROM ContentDocument"
            )["records"]
        ]
        self.logger.info(f"Found {len(self.return_values)} files")
        if len(self.return_values) > 0:
            self.logger.info(f"{'Id':<20} {'FileName':<50} {'FileType':<10}")

            # Print each row of the table
            for file_desc in self.return_values:
                self.logger.info(
                    f"{file_desc['Id']:<20} {file_desc['FileName']:<50} {file_desc['FileType']:<10}"
                )

        return self.return_values
