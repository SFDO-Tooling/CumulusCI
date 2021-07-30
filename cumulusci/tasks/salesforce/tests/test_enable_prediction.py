import unittest
from unittest.mock import MagicMock
from simple_salesforce import SalesforceError
from cumulusci.tasks.salesforce.enable_prediction import EnablePrediction
from cumulusci.core.exceptions import SalesforceException
from .util import create_task


class TestEnablePrediction(unittest.TestCase):
    def setUp(self):
        self.task = create_task(
            EnablePrediction, {"developer_name": "mlpd__test_prediction_v0"}
        )
        self.task.tooling = MagicMock()

    def test_run_task(self):
        self.task._get_ml_prediction_definition_id = MagicMock()
        self.task._get_ml_prediction_definition_id.return_value = "001"

        self.task.tooling.base_url = "http://test.salesforce.com/tooling/"
        self.task.tooling._call_salesforce().json.return_value = {
            "Metadata": {"status": "Draft"}
        }

        self.task._run_task()

        self.task.tooling._call_salesforce.assert_any_call(
            method="GET",
            url="http://test.salesforce.com/tooling/sobjects/MLPredictionDefinition/001",
        )

        self.task.tooling._call_salesforce.assert_any_call(
            method="PATCH",
            url="http://test.salesforce.com/tooling/sobjects/MLPredictionDefinition/001",
            json={"Metadata": {"status": "Enabled"}},
        )

    def test_run_task__exception(self):
        self.task._get_ml_prediction_definition_id = MagicMock()
        self.task._get_ml_prediction_definition_id.return_value = "001"

        self.task.tooling._call_salesforce.side_effect = MagicMock(
            side_effect=SalesforceError(None, None, None, "test exception")
        )

        self.assertRaises(SalesforceException, self.task._run_task)

    def test_get_ml_prediction_definition_id(self):
        self.task.tooling.query.return_value = {"records": [{"Id": "001"}]}

        self.assertEquals("001", self.task._get_ml_prediction_definition_id())

    def test_get_ml_prediction_definition_id__exception(self):
        self.task.tooling.query.side_effect = MagicMock(
            side_effect=SalesforceError("url", 500, "MLPredictionDefinition", "content")
        )

        with self.assertRaises(SalesforceException) as e:
            self.task._get_ml_prediction_definition_id()
        self.assertEqual(
            str(e.exception),
            "Failed to obtain MLPredictionDefinitionId: Unknown error occurred for url. Response content: content",
        )

        self.task.tooling.query.side_effect = MagicMock(side_effect=IndexError())

        with self.assertRaises(SalesforceException) as e:
            self.task._get_ml_prediction_definition_id()
        self.assertEqual(
            str(e.exception),
            "MLPredictionDefinition mlpd__test_prediction_v0 not found.",
        )
