from concurrent.futures import Future, ThreadPoolExecutor
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
from requests.exceptions import ConnectionError

from cumulusci.salesforce_api.retrieve_profile_api import RetrieveProfileApi


@pytest.fixture
def retrieve_profile_api_instance():
    sf_mock = MagicMock()
    bulk_mock = MagicMock()
    project_config = MagicMock()
    task_config = MagicMock()
    org_config = MagicMock()
    sf_mock.query.return_value = {"records": []}
    api = RetrieveProfileApi(
        project_config=project_config, org_config=org_config, task_config=task_config
    )
    api.sf = sf_mock
    api.bulk = bulk_mock
    return api


def test_run_query_sf(retrieve_profile_api_instance):
    query = "SELECT Id FROM Account"
    result_data = {"records": [{"Id": "001abc"}]}
    retrieve_profile_api_instance.sf.query.return_value = result_data

    result = retrieve_profile_api_instance._run_query(query)
    assert result == result_data


def test_run_query_bulk(retrieve_profile_api_instance):
    query = "SELECT Id FROM Account"
    result_data = {"records": [{"Id": "001abc"}]}
    retrieve_profile_api_instance.sf.query.side_effect = ConnectionError

    retrieve_profile_api_instance.bulk.create_query_job.return_value = "job_id"
    retrieve_profile_api_instance.bulk.query.return_value = "batch_id"
    retrieve_profile_api_instance.bulk.wait_for_batch.return_value = None
    retrieve_profile_api_instance.bulk.get_all_results_for_query_batch.return_value = [
        "some_value"
    ]

    with patch(
        "salesforce_bulk.util.IteratorBytesIO",
        return_value=StringIO('[{"Id": "001abc"}]'),
    ):
        result = retrieve_profile_api_instance._run_query(query)

    assert result == result_data


def test_extract_table_name_from_query_valid(retrieve_profile_api_instance):
    query = "SELECT Id FROM Account"
    table_name = retrieve_profile_api_instance._extract_table_name_from_query(query)
    assert table_name == "Account"


def test_extract_table_name_from_query_invalid(retrieve_profile_api_instance):
    query = "SELECT Id"
    with pytest.raises(ValueError):
        retrieve_profile_api_instance._extract_table_name_from_query(query)


def test_run_queries_in_parallel(retrieve_profile_api_instance):
    queries = {
        "query1": "SELECT * FROM Table1",
        "query2": "SELECT * FROM Table2",
    }

    expected_results = {
        "query1": [{"field1": "value1"}, {"field1": "value2"}],
        "query2": [{"field2": "value3"}, {"field2": "value4"}],
    }

    mock_future1 = MagicMock()
    mock_future1.result.return_value = {"records": expected_results["query1"]}
    mock_future2 = MagicMock()
    mock_future2.result.return_value = {"records": expected_results["query2"]}

    with patch.object(ThreadPoolExecutor, "submit") as mock_submit:
        mock_submit.side_effect = [mock_future1, mock_future2]

        results_dict = retrieve_profile_api_instance._run_queries_in_parallel(queries)

    assert results_dict == expected_results


def test_run_queries_in_parallel_with_exception(retrieve_profile_api_instance):
    queries = {
        "Query1": "SELECT Id FROM Table1",
    }

    with patch.object(Future, "result", side_effect=Exception("Test exception")):
        with pytest.raises(Exception) as excinfo:
            retrieve_profile_api_instance._run_queries_in_parallel(queries)
        assert (
            "Error executing query 'Query1': <class 'Exception'>: Test exception"
            == str(excinfo.value)
        )


def test_build_query_basic(retrieve_profile_api_instance):
    columns = ["Id", "Name"]
    table_name = "Account"
    expected_query = "SELECT Id, Name FROM Account"
    result_query = retrieve_profile_api_instance._build_query(columns, table_name)
    assert result_query == expected_query


def test_build_query_with_where(retrieve_profile_api_instance):
    columns = ["Id", "Name"]
    table_name = "Account"
    where = {"Type": "Customer", "Status": ["Active", "Inactive"]}
    expected_query = "SELECT Id, Name FROM Account WHERE Type = 'Customer' AND Status IN ('Active', 'Inactive')"
    result_query = retrieve_profile_api_instance._build_query(
        columns, table_name, where
    )
    assert result_query == expected_query


def test_build_query_empty_columns(retrieve_profile_api_instance):
    columns = []
    table_name = "Account"
    with pytest.raises(ValueError):
        retrieve_profile_api_instance._build_query(columns, table_name)


def test_build_query_empty_table_name(retrieve_profile_api_instance):
    columns = ["Id", "Name"]
    table_name = ""
    with pytest.raises(ValueError):
        retrieve_profile_api_instance._build_query(columns, table_name)


def test_process_sObject_results(retrieve_profile_api_instance):
    result_list = [
        {"SobjectType": "Account"},
        {"SobjectType": "Contact"},
        {"SobjectType": "Opportunity"},
    ]
    expected_result = {"CustomObject": ["Account", "Contact", "Opportunity"]}
    result = retrieve_profile_api_instance._process_sObject_results(result_list)
    assert result == expected_result


def test_process_sObject_results_missing_key(retrieve_profile_api_instance):
    result_list = [{"ObjectType": "Account"}]
    with pytest.raises(KeyError):
        retrieve_profile_api_instance._process_sObject_results(result_list)


def test_process_customTab_results(retrieve_profile_api_instance):
    result_list = [
        {"Name": "CustomTab1"},
        {"Name": "CustomTab2"},
        {"Name": "CustomTab3"},
    ]
    expected_result = {"CustomTab": ["CustomTab1", "CustomTab2", "CustomTab3"]}
    result = retrieve_profile_api_instance._process_customTab_results(result_list)
    assert result == expected_result


def test_process_customTab_results_missing_key(retrieve_profile_api_instance):
    result_list = [{"TabName": "CustomTab1"}]
    with pytest.raises(KeyError):
        retrieve_profile_api_instance._process_customTab_results(result_list)


def test_process_setupEntityAccess_results(retrieve_profile_api_instance):
    result_list = [
        {"SetupEntityType": "ApexClass", "SetupEntityId": "001abc"},
        {"SetupEntityType": "ApexPage", "SetupEntityId": "002def"},
        {"SetupEntityType": "CustomPermission", "SetupEntityId": "003ghi"},
    ]

    with patch.object(
        RetrieveProfileApi, "_build_query", return_value="SELECT Id, Name FROM Table"
    ) as mock_build_query, patch.object(
        RetrieveProfileApi,
        "_run_queries_in_parallel",
        return_value={
            "ApexClass": [
                {"Id": "001abc", "Name": "TestApexClass", "NamespacePrefix": "apex"}
            ],
            "ApexPage": [{"Id": "002def", "Name": "TestApexPage"}],
            "CustomPermission": [],
        },
    ) as mock_run_queries:

        result = retrieve_profile_api_instance._process_setupEntityAccess_results(
            result_list
        )
        mock_build_query.assert_any_call(
            ["Name", "NamespacePrefix"], "ApexClass", {"Id": ["001abc"]}
        )
        mock_build_query.assert_any_call(
            ["Name", "NamespacePrefix"], "ApexPage", {"Id": ["002def"]}
        )
        mock_build_query.assert_any_call(
            ["DeveloperName", "NamespacePrefix"], "CustomPermission", {"Id": ["003ghi"]}
        )
        mock_run_queries.assert_called_with(
            {
                "ApexClass": "SELECT Id, Name FROM Table",
                "ApexPage": "SELECT Id, Name FROM Table",
                "CustomPermission": "SELECT Id, Name FROM Table",
            }
        )

    expected_result = {
        "ApexClass": ["apex__TestApexClass"],
        "ApexPage": ["TestApexPage"],
        "CustomPermission": [],
    }
    assert result == expected_result


def test_retrieve_permissionable_entities(retrieve_profile_api_instance):
    profiles = ["Profile1", "Profile2"]

    with patch.object(
        RetrieveProfileApi, "_build_query"
    ) as mock_build_query, patch.object(
        RetrieveProfileApi, "_run_queries_in_parallel"
    ) as mock_run_queries, patch.object(
        RetrieveProfileApi,
        "_process_setupEntityAccess_results",
        return_value={"ApexClass": ["TestApexClass"], "ApexPage": ["TestApexPage"]},
    ), patch.object(
        RetrieveProfileApi,
        "_process_sObject_results",
        return_value={"CustomObject": ["TestObject"]},
    ), patch.object(
        RetrieveProfileApi,
        "_process_customTab_results",
        return_value={"CustomTab": ["TestTab"]},
    ):

        result = retrieve_profile_api_instance._retrieve_permissionable_entities(
            profiles
        )

        mock_build_query.assert_any_call(
            ["SetupEntityId", "SetupEntityType"],
            "SetupEntityAccess",
            {"Parent.Profile.Name": profiles},
        )
        mock_build_query.assert_any_call(
            ["SObjectType"], "ObjectPermissions", {"Parent.Profile.Name": profiles}
        )
        mock_build_query.assert_any_call(
            ["Name"], "PermissionSetTabSetting", {"Parent.Profile.Name": profiles}
        )

        expected_queries = {
            "setupEntityAccess": mock_build_query.return_value,
            "sObject": mock_build_query.return_value,
            "customTab": mock_build_query.return_value,
        }
        mock_run_queries.assert_called_with(expected_queries)

        expected_result = {
            "ApexClass": ["TestApexClass"],
            "ApexPage": ["TestApexPage"],
            "CustomObject": ["TestObject"],
            "CustomTab": ["TestTab"],
        }
        assert result == expected_result


if __name__ == "__main__":
    pytest.main()
