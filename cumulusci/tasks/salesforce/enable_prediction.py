from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.core.exceptions import SalesforceException
from simple_salesforce.exceptions import SalesforceError
from cumulusci.utils.http.requests_utils import safe_json_from_response


class EnablePrediction(BaseSalesforceApiTask):
    task_docs = """
    This task updates the state of Einstein Prediction Builder predictions from 'Draft' to 'Enabled' by
    posting to the metadata tooling API.

    cci task run enable_prediction --org dev -o developer_name mlpd__Example_Prediction_v0
    """

    task_options = {
        "developer_name": {
            "description": "Developer name of the MLPredictionDefinition.",
            "required": True,
        }
    }

    def _run_task(self):
        self._enable_prediction()

    def _enable_prediction(self):
        try:
            ml_prediction_definition_id = self._get_ml_prediction_definition_id()

            response = self.tooling._call_salesforce(
                method="GET",
                url=f"{self.tooling.base_url}sobjects/MLPredictionDefinition/{ml_prediction_definition_id}",
            )
            result = safe_json_from_response(response)
            metadata = result["Metadata"]

            metadata["status"] = "Enabled"

            self.tooling._call_salesforce(
                method="PATCH",
                url=f"{self.tooling.base_url}sobjects/MLPredictionDefinition/{ml_prediction_definition_id}",
                json={"Metadata": metadata},
            )
        except SalesforceError as e:
            raise SalesforceException(f"Failed to enable prediction: {e}")

    def _get_ml_prediction_definition_id(self):
        query = f"""
        select Id from MLPredictionDefinition where DeveloperName = '{self.options["developer_name"]}'
        """.strip()
        try:
            return self.tooling.query(query)["records"][0]["Id"]
        except IndexError:
            raise SalesforceException(
                f"MLPredictionDefinition {self.options['developer_name']} not found."
            )
        except SalesforceError as e:
            raise SalesforceException(f"Failed to obtain MLPredictionDefinitionId: {e}")
