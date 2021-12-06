# -*- coding: utf-8 -*-
import os
import re
from pprint import pformat
from unittest import mock

import pytest
from rich.emoji import Emoji
from rich.table import Column

from cumulusci.cli.ui import (
    CHECKMARK,
    CROSSMARK,
    CliTable,
    SimpleSalesforceUIHelpers,
    _summarize,
)


@pytest.fixture
def sample_data():
    return {
        "service_list": [
            ["Name", "Description", "Configured"],
            ["saucelabs", "Configure connection for saucelabs tasks.", False],
            ["sentry", "Configure connection to sentry.io for error tracking", False],
        ],
        "org_list": [
            [
                "Org",
                "Default",
                "Days",
                "Expired",
                "Config",
                Column("Domain", overflow="crop"),
            ],
            ["beta", None, 1, None, "beta", ""],
            ["dev", True, "1/7", False, "dev", "test-h8znvutwnctb@example.com"],
            ["feature", None, 1, None, "feature", ""],
        ],
        "task_list_util": [
            ["Task", "Description"],
            ["command", "Run an arbitrary command"],
            ["log", "Log a line at the info level."],
            ["util_sleep", "Sleeps for N seconds"],
        ],
    }


def test_table_dim_rows(sample_data):
    data = sample_data["service_list"]
    instance = CliTable(data, dim_rows=[1])
    assert instance.table.rows[0].style.dim


def test_table_stringify_booleans(sample_data):
    data = sample_data["service_list"]
    data[1][2] = True
    CliTable.PICTOGRAM_TRUE = CHECKMARK
    CliTable.PICTOGRAM_FALSE = CROSSMARK
    instance = CliTable(data)
    table = str(instance)
    if os.name == "posix":
        assert Emoji.replace(":heavy_check_mark:") in table
        assert Emoji.replace(":cross_mark:") in table
    else:
        assert "+" in table
        assert "-" in table


def test_table_stringify_misc(sample_data):
    data = sample_data["org_list"]
    instance = CliTable(data)
    table = str(instance)
    assert "7" in table
    assert "None" not in table


def test_columnify_headers():
    data = [["y", Column("n", overflow="crop"), 43], [1, 2, 3]]
    table = CliTable(data)
    str(table)
    formatted_table = str(table)
    assert "  y   n   43  " in formatted_table


def test_rich_truncation(sample_data):
    count = 6
    data = [["column"], ["x" * 16 * count]]
    table = CliTable(data, title="testerino", width=20)
    formatted_table = str(table)
    rxp = re.compile("x{16}")
    assert len(rxp.findall(formatted_table)) == count


PRETEND_DESCRIBE_DATA = {
    "name": "Blah",
    "updateable": False,
    "fields": [
        {"name": "Foo", "referenceTo": ["Bar"], "picklistValues": []},
        {
            "name": "Bar",
            "referenceTo": [],
            "picklistValues": [{"value": "a"}, {"value": "b"}],
        },
        {"name": "Baz", "type": "string", "referenceTo": [], "picklistValues": []},
    ],
}

SUMMARIZED_DATA = {"Foo": ["Bar"], "Bar": ["a", "b"], "Baz": "string"}


def test_summarize():
    fields = PRETEND_DESCRIBE_DATA["fields"]
    assert _summarize(fields[0]) == ("Foo", ["Bar"])
    assert _summarize(fields[1]) == ("Bar", ["a", "b"])
    assert _summarize(fields[2]) == ("Baz", "string")


def test_pretty_describe():
    sf = mock.MagicMock()
    sf.Blah.describe.return_value = PRETEND_DESCRIBE_DATA
    rc = SimpleSalesforceUIHelpers(sf).describe("Blah", detailed=False, format="obj")
    assert sf.Blah.describe.mock_calls
    assert rc == SUMMARIZED_DATA, rc


def test_pretty_describe_detailed():
    sf = mock.MagicMock()
    sf.Blah.describe.return_value = PRETEND_DESCRIBE_DATA
    rc = SimpleSalesforceUIHelpers(sf).describe("Blah", detailed=True, format="obj")
    assert sf.Blah.describe.mock_calls
    assert rc == PRETEND_DESCRIBE_DATA, rc


def test_pretty_describe_pprint(capsys):
    sf = mock.MagicMock()
    sf.Blah.describe.return_value = PRETEND_DESCRIBE_DATA
    SimpleSalesforceUIHelpers(sf).describe("Blah", detailed=False, format="pprint")
    out = capsys.readouterr().out
    assert sf.Blah.describe.mock_calls
    assert out.strip() == pformat(SUMMARIZED_DATA), (out, pformat(SUMMARIZED_DATA))


def test_pretty_describe_format_error():
    sf = mock.MagicMock()
    sf.Blah.describe.return_value = PRETEND_DESCRIBE_DATA
    with pytest.raises(TypeError):
        SimpleSalesforceUIHelpers(sf).describe("Blah", detailed=False, format="xyzzy")


def _pretend_soql_result(*args):
    return {
        "totalSize": 1,
        "done": True,
        "records": [{"attributes": {"type": "AggregateResult"}, "expr0": 20}],
    }


def _pretend_soql_results(num_records):
    rc = {"totalSize": 1, "done": True, "records": []}
    for i in range(0, num_records):
        rc["records"].append(
            {"attributes": {"type": "AggregateResult"}, "Id": "00GUSWLMA"}
        )
    return rc


def test_pretty_soql_query_simple_count():
    sf = mock.MagicMock()
    sf.query_all.return_value = _pretend_soql_result()
    rc = SimpleSalesforceUIHelpers(sf).query(
        "select Count(Id) from Account",
        include_deleted=False,
        format="obj",
        max_rows=100,
    )
    assert sf.query_all.mock_calls == [
        mock.call("select Count(Id) from Account", include_deleted=False)
    ], sf.query_all.mock_calls
    assert rc == [{"expr0": 20}]

    sf = mock.MagicMock()
    sf.query_all.return_value = _pretend_soql_result()

    rc = SimpleSalesforceUIHelpers(sf).query(
        "select Count(Id) from Account",
        include_deleted=True,
        format="obj",
        max_rows=100,
    )
    assert sf.query_all.mock_calls == [
        mock.call("select Count(Id) from Account", include_deleted=True)
    ], sf.query_all.mock_calls
    assert rc == [{"expr0": 20}]


def test_pretty_soql_query_simple_truncation():
    sf = mock.MagicMock()
    sf.query_all.return_value = _pretend_soql_results(150)
    rc = SimpleSalesforceUIHelpers(sf).query(
        "select Id from Account", include_deleted=False, format="obj", max_rows=100
    )
    assert sf.query_all.mock_calls == [
        mock.call("select Id from Account", include_deleted=False)
    ], sf.query_all.mock_calls
    assert len(rc) == 101, len(rc)
    assert rc[-1] == "... truncated 50 rows"


def test_pretty_soql_query_table(capsys):
    sf = mock.MagicMock()
    sf.query_all.return_value = _pretend_soql_result()

    SimpleSalesforceUIHelpers(sf).query(
        "select Count(Id) from Account",
        include_deleted=False,
        format="table",
        max_rows=100,
    )
    assert sf.query_all.mock_calls == [
        mock.call("select Count(Id) from Account", include_deleted=False)
    ], sf.query_all.mock_calls
    out = capsys.readouterr().out

    assert "expr0" in out
    assert "20" in out
    assert "help" in out


def test_pretty_soql_query_table_truncation(capsys):
    sf = mock.MagicMock()
    sf.query_all.return_value = _pretend_soql_results(150)

    SimpleSalesforceUIHelpers(sf).query(
        "select Id from Account",
        include_deleted=False,
        format="table",
        max_rows=100,
    )
    assert sf.query_all.mock_calls == [
        mock.call("select Id from Account", include_deleted=False)
    ], sf.query_all.mock_calls
    out = capsys.readouterr().out
    assert out.count("00GUSWLMA") == 100


def test_pretty_table_empty(capsys):
    sf = mock.MagicMock()
    sf.query_all.return_value = _pretend_soql_results(0)

    SimpleSalesforceUIHelpers(sf).query(
        "select Id from Account", include_deleted=False, format="table", max_rows=100
    )
    assert sf.query_all.mock_calls == [
        mock.call("select Id from Account", include_deleted=False)
    ], sf.query_all.mock_calls
    out = capsys.readouterr().out
    assert out.count("00GUSWLMA") == 0
    assert "No results" in out


def test_pretty_soql_query_pprint(capsys):
    sf = mock.MagicMock()
    sf.query_all.return_value = _pretend_soql_results(150)

    SimpleSalesforceUIHelpers(sf).query(
        "select Id from Account", include_deleted=False, format="pprint", max_rows=100
    )
    assert sf.query_all.mock_calls == [
        mock.call("select Id from Account", include_deleted=False)
    ], sf.query_all.mock_calls
    out = capsys.readouterr().out
    assert out.count("00GUSWLMA") == 100


def test_pretty_soql_query_json():
    sf = mock.MagicMock()
    sf.query_all.return_value = _pretend_soql_results(150)

    rc = SimpleSalesforceUIHelpers(sf).query(
        "select Id from Account", include_deleted=False, format="json", max_rows=100
    )
    assert sf.query_all.mock_calls == [
        mock.call("select Id from Account", include_deleted=False)
    ], sf.query_all.mock_calls

    assert rc.count("00GUSWLMA") == 100


def test_pretty_soql_query_errors():
    sf = mock.MagicMock()
    sf.query_all.return_value = _pretend_soql_results(150)

    with pytest.raises(TypeError):
        SimpleSalesforceUIHelpers(sf).query(
            "select Id from Account",
            include_deleted=False,
            format="punchcard",
            max_rows=100,
        )


@mock.patch("cumulusci.cli.ui.SimpleSalesforceUIHelpers.query")
@mock.patch("cumulusci.cli.ui.SimpleSalesforceUIHelpers.describe")
def test_repl_helpers(pretty_soql_query, pretty_describe):
    sf = mock.MagicMock()
    helpers = SimpleSalesforceUIHelpers(sf)
    assert helpers.describe("Account", format="obj")
    assert helpers.query("select Id from Account", format="obj")
