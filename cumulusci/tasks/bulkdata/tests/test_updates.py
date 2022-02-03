# from unittest import mock

import pytest

from cumulusci.core import exceptions as exc
from cumulusci.tasks.bulkdata.update_data import UpdateData


def mock_fake_query_operation(**expected):
    def fake_get_query_operation(
        **given,
    ):
        assert given == expected
        return FakeQueryResult(["blah"])


class FakeQueryResult:
    def __init__(self, results, numrecords=None):
        self.results = results
        if numrecords is None:
            numrecords = len(self.results)
        self.numrecords = numrecords

    def yield_per(self, number):
        return self.results

    def count(self):
        return self.numrecords


class TestUpdates:
    def test_options__bad_sobject(self, create_task):
        with pytest.raises(exc.TaskOptionsError) as e:
            task = create_task(UpdateData, {"object": "a b c"})
            task()
        assert "a b c" in str(e.value), e.value

    def test_options__bad_field(self, create_task):
        with pytest.raises(exc.TaskOptionsError) as e:
            task = create_task(UpdateData, {"object": "Account", "fields": ["a b c"]})
            task()
        assert "a b c" in str(e.value), e.value

    def test_options__bad_fields(self, create_task):
        with pytest.raises(exc.TaskOptionsError) as e:
            task = create_task(
                UpdateData, {"object": "Account", "fields": ["a b c", "1 2 3"]}
            )
            task()
        assert "a b c" in str(e.value), e.value

    def test_options__bad_api(self, create_task):
        with pytest.raises(exc.TaskOptionsError) as e:
            task = create_task(UpdateData, {"object": "Account", "api": "XML-RPC"})
            task()
        assert "XML-RPC" in str(e.value), e.value

    # @mock.patch(
    #     "cumulusci.tasks.bulkdata.update_data.get_query_operation",
    #     mock_fake_query_operation(),
    # )
    # def test_with_fake_query_results(self, create_task):
    #     task = create_task(
    #         UpdateData, {"object": "Account", "recipe": "datasets/update.recipe.yml"}
    #     )

    #     def _validate_and_inject_namespace_prefixes():
    #         pass

    #     task._validate_and_inject_namespace_prefixes
    #     task()
