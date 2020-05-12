# -*- coding: utf-8 -*-
import sys

from unittest import mock
from pprint import pformat

import pytest
from cumulusci.cli.ui import CHECKMARK, CliTable, _summarize, SimpleSalesforceUIHelpers


@pytest.fixture
def sample_data():
    return {
        "service_list": [
            ["Name", "Description", "Configured"],
            ["saucelabs", "Configure connection for saucelabs tasks.", False],
            ["sentry", "Configure connection to sentry.io for error tracking", False],
        ],
        "org_list": [
            ["Org", "Default", "Scratch", "Days", "Expired", "Config", "Username"],
            ["beta", None, True, 1, None, "beta", ""],
            ["dev", True, True, "1/7", False, "dev", "test-h8znvutwnctb@example.com"],
            ["feature", None, True, 1, None, "feature", ""],
        ],
        "task_list_util": [
            ["Task", "Description"],
            ["command", "Run an arbitrary command"],
            ["log", "Log a line at the info level."],
            ["util_sleep", "Sleeps for N seconds"],
        ],
    }


@pytest.fixture
def pretty_output():
    return {
        "service_list": "\x1b(0lqqqqqqqqqqqwqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqwqqqqqqqqqqqqk\x1b(B\n\x1b(0x\x1b(B Name      \x1b(0x\x1b(B Description                                          \x1b(0x\x1b(B Configured \x1b(0x\x1b(B\n\x1b(0tqqqqqqqqqqqnqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqnqqqqqqqqqqqqu\x1b(B\n\x1b(0x\x1b(B saucelabs \x1b(0x\x1b(B Configure connection for saucelabs tasks.            \x1b(0x\x1b(B False      \x1b(0x\x1b(B\n\x1b(0x\x1b(B sentry    \x1b(0x\x1b(B Configure connection to sentry.io for error tracking \x1b(0x\x1b(B False      \x1b(0x\x1b(B\n\x1b(0mqqqqqqqqqqqvqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqvqqqqqqqqqqqqj\x1b(B",
        "org_list": "\x1b(0lqqqqqqqqqwqqqqqqqqqwqqqqqqqqqwqqqqqqwqqqqqqqqqwqqqqqqqqqwqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqk\x1b(B\n\x1b(0x\x1b(B Org     \x1b(0x\x1b(B Default \x1b(0x\x1b(B Scratch \x1b(0x\x1b(B Days \x1b(0x\x1b(B Expired \x1b(0x\x1b(B Config  \x1b(0x\x1b(B Username                      \x1b(0x\x1b(B\n\x1b(0tqqqqqqqqqnqqqqqqqqqnqqqqqqqqqnqqqqqqnqqqqqqqqqnqqqqqqqqqnqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqu\x1b(B\n\x1b(0x\x1b(B beta    \x1b(0x\x1b(B None    \x1b(0x\x1b(B True    \x1b(0x\x1b(B 1    \x1b(0x\x1b(B None    \x1b(0x\x1b(B beta    \x1b(0x\x1b(B                               \x1b(0x\x1b(B\n\x1b(0x\x1b(B dev     \x1b(0x\x1b(B True    \x1b(0x\x1b(B True    \x1b(0x\x1b(B 1/7  \x1b(0x\x1b(B False   \x1b(0x\x1b(B dev     \x1b(0x\x1b(B test-h8znvutwnctb@example.com \x1b(0x\x1b(B\n\x1b(0x\x1b(B feature \x1b(0x\x1b(B None    \x1b(0x\x1b(B True    \x1b(0x\x1b(B 1    \x1b(0x\x1b(B None    \x1b(0x\x1b(B feature \x1b(0x\x1b(B                               \x1b(0x\x1b(B\n\x1b(0mqqqqqqqqqvqqqqqqqqqvqqqqqqqqqvqqqqqqvqqqqqqqqqvqqqqqqqqqvqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqj\x1b(B",
        "task_list_util": "\x1b(0lqqqqqqqqqqqqwqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqk\x1b(B\n\x1b(0x\x1b(B Task       \x1b(0x\x1b(B Description                   \x1b(0x\x1b(B\n\x1b(0tqqqqqqqqqqqqnqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqu\x1b(B\n\x1b(0x\x1b(B command    \x1b(0x\x1b(B Run an arbitrary command      \x1b(0x\x1b(B\n\x1b(0x\x1b(B log        \x1b(0x\x1b(B Log a line at the info level. \x1b(0x\x1b(B\n\x1b(0x\x1b(B util_sleep \x1b(0x\x1b(B Sleeps for N seconds          \x1b(0x\x1b(B\n\x1b(0mqqqqqqqqqqqqvqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqj\x1b(B",
    }


@pytest.fixture
def pretty_output_win():
    return {
        "service_list": u"""
┌───────────┬──────────────────────────────────────────────────────┬────────────┐
│ Name      │ Description                                          │ Configured │
├───────────┼──────────────────────────────────────────────────────┼────────────┤
│ saucelabs │ Configure connection for saucelabs tasks.            │ False      │
│ sentry    │ Configure connection to sentry.io for error tracking │ False      │
└───────────┴──────────────────────────────────────────────────────┴────────────┘""",
        "org_list": u"""
┌─────────┬─────────┬─────────┬──────┬─────────┬─────────┬───────────────────────────────┐
│ Org     │ Default │ Scratch │ Days │ Expired │ Config  │ Username                      │
├─────────┼─────────┼─────────┼──────┼─────────┼─────────┼───────────────────────────────┤
│ beta    │ None    │ True    │ 1    │ None    │ beta    │                               │
│ dev     │ True    │ True    │ 1/7  │ False   │ dev     │ test-h8znvutwnctb@example.com │
│ feature │ None    │ True    │ 1    │ None    │ feature │                               │
└─────────┴─────────┴─────────┴──────┴─────────┴─────────┴───────────────────────────────┘
""",
        "task_list_util": u"""
┌────────────┬───────────────────────────────┐
│ Task       │ Description                   │
├────────────┼───────────────────────────────┤
│ command    │ Run an arbitrary command      │
│ log        │ Log a line at the info level. │
│ util_sleep │ Sleeps for N seconds          │
└────────────┴───────────────────────────────┘
""",
    }


@pytest.fixture
def plain_output():
    return {
        "service_list": """+-----------------------------------------------------------------------------+
| Name       Description                                           Configured |
+-----------------------------------------------------------------------------+
| saucelabs  Configure connection for saucelabs tasks.             False      |
| sentry     Configure connection to sentry.io for error tracking  False      |
+-----------------------------------------------------------------------------+
""",
        "org_list": """+----------------------------------------------------------------------------------+
| Org      Default  Scratch  Days  Expired  Config   Username                      |
+----------------------------------------------------------------------------------+
| beta     None     True     1     None     beta                                   |
| dev      True     True     1/7   False    dev      test-h8znvutwnctb@example.com |
| feature  None     True     1     None     feature                                |
+----------------------------------------------------------------------------------+
""",
        "task_list_util": """+-------------------------------------------+
| Task        Description                   |
+-------------------------------------------+
| command     Run an arbitrary command      |
| log         Log a line at the info level. |
| util_sleep  Sleeps for N seconds          |
+-------------------------------------------+
""",
    }


@pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="Windows uses unicode chars instead of ASCII box chars.",
)
@pytest.mark.parametrize("fixture_key", ["service_list", "org_list", "task_list_util"])
def test_table_pretty_output(sample_data, pretty_output, fixture_key):
    instance = CliTable(sample_data[fixture_key])
    instance.INNER_BORDER = False
    table = instance.pretty_table()
    expected = pretty_output[fixture_key] + "\n"
    assert expected == table


@pytest.mark.skipif(
    not sys.platform.startswith("win"),
    reason="Windows uses unicode chars instead of ASCII box chars.",
)
@pytest.mark.parametrize("fixture_key", ["service_list"])
def test_table_pretty_output_windows(sample_data, pretty_output_win, fixture_key):
    instance = CliTable(sample_data[fixture_key])
    instance.INNER_BORDER = False
    table = instance.pretty_table().strip()
    expected = pretty_output_win[fixture_key].strip()
    assert expected == table


@pytest.mark.parametrize("fixture_key", ["service_list", "org_list", "task_list_util"])
def test_table_plain_output(sample_data, plain_output, fixture_key, capsys):
    instance = CliTable(sample_data[fixture_key])
    table = instance.ascii_table()
    expected = plain_output[fixture_key].strip()
    assert expected == table


@pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="Windows uses unicode chars instead of ASCII box chars.",
)
@pytest.mark.parametrize("fixture_key", ["service_list", "org_list", "task_list_util"])
def test_table_pretty_echo(sample_data, pretty_output, fixture_key, capsys):
    instance = CliTable(sample_data[fixture_key])
    instance.INNER_BORDER = False
    instance.echo(plain=False)

    captured = capsys.readouterr()
    expected = pretty_output[fixture_key] + "\n\n"
    assert expected == captured.out


@pytest.mark.parametrize("fixture_key", ["service_list", "org_list", "task_list_util"])
def test_table_plain_echo(sample_data, plain_output, fixture_key, capsys):
    instance = CliTable(sample_data[fixture_key])
    instance.echo(plain=True)
    captured = capsys.readouterr()
    expected = plain_output[fixture_key]
    assert expected == captured.out


def test_table_plain_fallback(sample_data, plain_output, capsys):
    with mock.patch("cumulusci.cli.ui.CliTable.pretty_table") as pretty_table:
        pretty_table.side_effect = UnicodeEncodeError(
            "cp1542", u"", 42, 43, "Fake exception"
        )
        instance = CliTable(sample_data["service_list"])
        instance.echo(plain=False)
        captured = capsys.readouterr()
        # append newlines because echo adds them to account for task tables
        assert plain_output["service_list"] == captured.out


@pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="Click.echo does not support row dimming on Windows.",
)
def test_table_dim_rows(sample_data):
    data = sample_data["service_list"]
    instance = CliTable(data, dim_rows=[1])
    assert all(
        (
            cell.startswith("\x1b[2m") and cell.endswith("\x1b[0m")
            for cell in instance._table.table_data[1]
        )
    )


def test_table_stringify_booleans(sample_data):
    data = sample_data["service_list"]
    data[1][2] = True
    instance = CliTable(data, bool_cols=["Configured"])
    assert CHECKMARK in instance._table.table_data[1]
    assert CliTable.PICTOGRAM_FALSE in instance._table.table_data[2]


@mock.patch("terminaltables.SingleTable.column_max_width")
def test_table_wrap_cols(max_width, sample_data):
    width = 80
    max_width.return_value = width
    data = sample_data["service_list"]
    data[1][1] = data[1][1] + "a" * 256
    instance = CliTable(data, wrap_cols=["Description"])
    assert all((len(line) for line in instance._table.table_data[1][1].split("\n")))


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


def pretty_table_raises(*args):
    """If the pretty_table method raises, CliTable will
    use ascii_table which is easier to deal with for
    checking correctness """
    raise UnicodeEncodeError("a", "b", 0, 0, "e")


def test_pretty_soql_query_table(capsys):
    sf = mock.MagicMock()
    sf.query_all.return_value = _pretend_soql_result()

    with mock.patch("cumulusci.cli.ui.CliTable.pretty_table", pretty_table_raises):
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

    def pretty_table_raises(*args):
        raise UnicodeEncodeError("a", "b", 0, 0, "e")

    with mock.patch("cumulusci.cli.ui.CliTable.pretty_table", pretty_table_raises):
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
