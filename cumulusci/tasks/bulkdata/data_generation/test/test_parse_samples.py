import unittest
import pathlib
import mock

from cumulusci.tasks.bulkdata.data_generation.data_generator import generate

dnd_test = pathlib.Path(__file__).parent / "CharacterGenTest.yml"
data_imports = pathlib.Path(__file__).parent / "BDI_Generator.yml"
standard_objects = pathlib.Path(__file__).parent / "gen_sf_standard_objects.yml"


def find_row(row_type, compare, calls):
    for call in calls:
        call_row_type, call_dict = call.args
        if call_row_type == row_type and all(
            compare[key] == call_dict[key] for key in compare.keys()
        ):
            return call


write_row_path = "cumulusci.tasks.bulkdata.data_generation.output_streams.DebugOutputStream.write_row"


class TestParseAndOutput(unittest.TestCase):
    @mock.patch(write_row_path)
    def test_d_and_d(self, write_row):
        with open(dnd_test) as open_yaml_file:
            generate(
                open_yaml_file, 1, {"num_fighters": 1, "num_druids": 2}, None, None
            )
        calls = write_row.mock_calls
        assert find_row("Equipment", {"id": 1}, calls)
        assert find_row("Druid", {"id": 1, "Hit Points": mock.ANY}, calls)
        assert find_row("Druid", {"id": 2, "Hit Points": mock.ANY}, calls)
        assert find_row("Fighter", {"id": 1, "Name": mock.ANY}, calls)
        assert not find_row("Fighter", {"id": 2, "Name": mock.ANY}, calls)
        assert find_row("Paladin", {"id": 1, "Name": mock.ANY}, calls)

    @mock.patch(write_row_path)
    def test_data_imports(self, write_row):
        with open(data_imports) as open_yaml_file:
            generate(open_yaml_file, 1, {"total_data_imports": 4}, None, None)
        calls = write_row.mock_calls
        assert find_row(
            "General_Accounting_Unit__c", {"id": 1, "Name": "Scholarship"}, calls
        )

        assert find_row(
            "DataImport__c", {"id": 1, "Account1_Street__c": "Cordova Street"}, calls
        )

        assert find_row(
            "Account",
            {
                "id": 1,
                "BillingStreet": "Cordova Street",
                "BillingCountry": "Tuvalu",
                "description": "Pre-existing",
                "record_type": "HH_Account",
            },
            calls,
        )

    @mock.patch(write_row_path)
    def test_gen_standard_objects(self, write_row):
        with open(standard_objects) as open_yaml_file:
            generate(open_yaml_file, 1, {}, None, None)

        calls = write_row.mock_calls

        assert find_row("Account", {}, calls)
        assert find_row("Contact", {}, calls)
        assert find_row("Opportunity", {}, calls)
