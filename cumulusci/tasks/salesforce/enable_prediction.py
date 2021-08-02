from simple_salesforce.exceptions import SalesforceError

from cumulusci.core.exceptions import CumulusCIException
from cumulusci.core.utils import process_bool_arg, process_list_arg
from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.utils import inject_namespace
from cumulusci.utils.http.requests_utils import safe_json_from_response


class EnablePrediction(BaseSalesforceApiTask):
    task_docs = """
    This task updates the state of Einstein Prediction Builder predictions from 'Draft' to 'Enabled' by
    posting to the Tooling API.

    cci task run enable_prediction --org dev -o api_names Example_Prediction_v0
    """

    task_options = {
        "managed": {
            "description": "If False, changes namespace_inject to replace tokens with a blank string"
        },
        "namespaced_org": {
            "description": "If False, changes namespace_inject to replace namespaced-org tokens with a blank string"
        },
        "namespace_inject": {
            "description": "If set, the namespace tokens in files and filenames are replaced with the namespace's prefix"
        },
        "api_names": {
            "description": "List of API names of the MLPredictionDefinitions.",
            "required": True,
        },
    }

    def _init_namespace_injection(self):
        namespace = (
            self.options.get("namespace_inject")
            or self.project_config.project__package__namespace
        )
        self.options["namespace_inject"] = namespace
        if "managed" in self.options:
            self.options["managed"] = process_bool_arg(self.options["managed"] or False)
        else:
            self.options["managed"] = (
                bool(namespace) and namespace in self.org_config.installed_packages
            )
        if "namespaced_org" in self.options:
            self.options["namespaced_org"] = process_bool_arg(
                self.options["namespaced_org"] or False
            )
        else:
            self.options["namespaced_org"] = (
                bool(namespace) and namespace == self.org_config.namespace
            )

    def _inject_namespace(self, text):
        """Inject the namespace into the given text if running in managed mode."""
        # We might not have an org yet if this is called from _init_options
        # while freezing steps for metadeploy.
        if self.org_config is None:
            return text
        return inject_namespace(
            "",
            text,
            namespace=self.options["namespace_inject"],
            managed=self.options.get("managed") or False,
            namespaced_org=self.options.get("namespaced_org"),
        )[1]

    def _run_task(self):
        # org_config might be None if we're freezing steps for metadeploy.
        # We can only autodetect the context for namespace injection if we have the org.
        if self.org_config:
            self._init_namespace_injection()

        api_names = [
            self._inject_namespace(api_name)
            for api_name in process_list_arg(self.options["api_names"])
        ]

        for api_name in api_names:
            try:
                ml_prediction_definition_id = self._get_ml_prediction_definition_id(
                    api_name
                )

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
                raise CumulusCIException(f"Failed to enable prediction: {e}")

    def _get_ml_prediction_definition_id(self, api_name: str):
        query = (
            f"SELECT Id FROM MLPredictionDefinition WHERE DeveloperName = '{api_name}'"
        )
        try:
            return self.tooling.query(query)["records"][0]["Id"]
        except IndexError:
            raise CumulusCIException(f"MLPredictionDefinition {api_name} not found.")
