import mock
import pytest
from cumulusci.cli.ui import CliTable


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
        "task_list_robot": [
            ["Task", "Description"],
            ["robot", "Runs a Robot Framework test from a .robot file"],
            [
                "robot_libdoc",
                "Generates html documentation for the Salesorce and CumulusCI libraries and resource files",
            ],
        ],
    }


@pytest.fixture
def pretty_output():
    return {
        "service_list": "\x1b(0lqqqqqqqqqqqwqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqwqqqqqqqqqqqqk\x1b(B\n\x1b(0x\x1b(B Name      \x1b(0x\x1b(B Description                                          \x1b(0x\x1b(B Configured \x1b(0x\x1b(B\n\x1b(0tqqqqqqqqqqqnqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqnqqqqqqqqqqqqu\x1b(B\n\x1b(0x\x1b(B saucelabs \x1b(0x\x1b(B Configure connection for saucelabs tasks.            \x1b(0x\x1b(B False      \x1b(0x\x1b(B\n\x1b(0x\x1b(B sentry    \x1b(0x\x1b(B Configure connection to sentry.io for error tracking \x1b(0x\x1b(B False      \x1b(0x\x1b(B\n\x1b(0mqqqqqqqqqqqvqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqvqqqqqqqqqqqqj\x1b(B",
        "org_list": "\x1b(0lqqqqqqqqqwqqqqqqqqqwqqqqqqqqqwqqqqqqwqqqqqqqqqwqqqqqqqqqwqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqk\x1b(B\n\x1b(0x\x1b(B Org     \x1b(0x\x1b(B Default \x1b(0x\x1b(B Scratch \x1b(0x\x1b(B Days \x1b(0x\x1b(B Expired \x1b(0x\x1b(B Config  \x1b(0x\x1b(B Username                      \x1b(0x\x1b(B\n\x1b(0tqqqqqqqqqnqqqqqqqqqnqqqqqqqqqnqqqqqqnqqqqqqqqqnqqqqqqqqqnqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqu\x1b(B\n\x1b(0x\x1b(B beta    \x1b(0x\x1b(B None    \x1b(0x\x1b(B True    \x1b(0x\x1b(B 1    \x1b(0x\x1b(B None    \x1b(0x\x1b(B beta    \x1b(0x\x1b(B                               \x1b(0x\x1b(B\n\x1b(0x\x1b(B dev     \x1b(0x\x1b(B True    \x1b(0x\x1b(B True    \x1b(0x\x1b(B 1/7  \x1b(0x\x1b(B False   \x1b(0x\x1b(B dev     \x1b(0x\x1b(B test-h8znvutwnctb@example.com \x1b(0x\x1b(B\n\x1b(0x\x1b(B feature \x1b(0x\x1b(B None    \x1b(0x\x1b(B True    \x1b(0x\x1b(B 1    \x1b(0x\x1b(B None    \x1b(0x\x1b(B feature \x1b(0x\x1b(B                               \x1b(0x\x1b(B\n\x1b(0mqqqqqqqqqvqqqqqqqqqvqqqqqqqqqvqqqqqqvqqqqqqqqqvqqqqqqqqqvqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqj\x1b(B",
        "task_list_util": "\x1b(0lqqqqqqqqqqqqwqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqk\x1b(B\n\x1b(0x\x1b(B Task       \x1b(0x\x1b(B Description                   \x1b(0x\x1b(B\n\x1b(0tqqqqqqqqqqqqnqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqu\x1b(B\n\x1b(0x\x1b(B command    \x1b(0x\x1b(B Run an arbitrary command      \x1b(0x\x1b(B\n\x1b(0x\x1b(B log        \x1b(0x\x1b(B Log a line at the info level. \x1b(0x\x1b(B\n\x1b(0x\x1b(B util_sleep \x1b(0x\x1b(B Sleeps for N seconds          \x1b(0x\x1b(B\n\x1b(0mqqqqqqqqqqqqvqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqj\x1b(B",
        "task_list_robot": "\x1b(0lqqqqqqqqqqqqqqwqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqk\x1b(B\n\x1b(0x\x1b(B Task         \x1b(0x\x1b(B Description                                                                               \x1b(0x\x1b(B\n\x1b(0tqqqqqqqqqqqqqqnqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqu\x1b(B\n\x1b(0x\x1b(B robot        \x1b(0x\x1b(B Runs a Robot Framework test from a .robot file                                            \x1b(0x\x1b(B\n\x1b(0x\x1b(B robot_libdoc \x1b(0x\x1b(B Generates html documentation for the Salesorce and CumulusCI libraries and resource files \x1b(0x\x1b(B\n\x1b(0mqqqqqqqqqqqqqqvqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqj\x1b(B",
    }


@pytest.fixture
def plain_output():
    return {
        "service_list": """+-----------+------------------------------------------------------+------------+
| Name      | Description                                          | Configured |
+-----------+------------------------------------------------------+------------+
| saucelabs | Configure connection for saucelabs tasks.            | False      |
+-----------+------------------------------------------------------+------------+
| sentry    | Configure connection to sentry.io for error tracking | False      |
+-----------+------------------------------------------------------+------------+
""",
        "org_list": """+---------+---------+---------+------+---------+---------+-------------------------------+
| Org     | Default | Scratch | Days | Expired | Config  | Username                      |
+---------+---------+---------+------+---------+---------+-------------------------------+
| beta    | None    | True    | 1    | None    | beta    |                               |
+---------+---------+---------+------+---------+---------+-------------------------------+
| dev     | True    | True    | 1/7  | False   | dev     | test-h8znvutwnctb@example.com |
+---------+---------+---------+------+---------+---------+-------------------------------+
| feature | None    | True    | 1    | None    | feature |                               |
+---------+---------+---------+------+---------+---------+-------------------------------+
""",
        "task_list_util": """+------------+-------------------------------+
| Task       | Description                   |
+------------+-------------------------------+
| command    | Run an arbitrary command      |
+------------+-------------------------------+
| log        | Log a line at the info level. |
+------------+-------------------------------+
| util_sleep | Sleeps for N seconds          |
+------------+-------------------------------+
""",
        "task_list_robot": """+--------------+-------------------------------------------------------------------------------------------+
| Task         | Description                                                                               |
+--------------+-------------------------------------------------------------------------------------------+
| robot        | Runs a Robot Framework test from a .robot file                                            |
+--------------+-------------------------------------------------------------------------------------------+
| robot_libdoc | Generates html documentation for the Salesorce and CumulusCI libraries and resource files |
+--------------+-------------------------------------------------------------------------------------------+
""",
    }


@pytest.mark.parametrize(
    "fixture_key", ["service_list", "org_list", "task_list_util", "task_list_robot"]
)
def test_table_pretty_output(sample_data, pretty_output, fixture_key):
    instance = CliTable(sample_data[fixture_key])
    assert pretty_output[fixture_key] == instance.table.table


@pytest.mark.parametrize(
    "fixture_key", ["service_list", "org_list", "task_list_util", "task_list_robot"]
)
def test_table_plain_output(sample_data, plain_output, fixture_key, capsys):
    instance = CliTable(sample_data[fixture_key])
    instance.ascii_table()
    captured = capsys.readouterr()
    assert plain_output[fixture_key] == captured.out


@pytest.mark.parametrize(
    "fixture_key", ["service_list", "org_list", "task_list_util", "task_list_robot"]
)
def test_table_plain_echo(sample_data, plain_output, fixture_key, capsys):
    instance = CliTable(sample_data[fixture_key])
    instance.echo(plain=True)
    captured = capsys.readouterr()
    assert plain_output[fixture_key] == captured.out


def test_table_plain_fallback(sample_data, plain_output, capsys):
    with mock.patch("cumulusci.cli.ui.CliTable.pretty_table") as pretty_table:
        pretty_table.side_effect = UnicodeEncodeError(
            "cp1542", "", 42, 43, "Fake exception"
        )
        instance = CliTable(sample_data["service_list"])
        instance.echo(plain=False)
        captured = capsys.readouterr()
        # append newlines because echo adds them to account for task tables
        assert plain_output["service_list"] + "\n\n" == captured.out


def test_table_stringify_booleans(sample_data):
    data = sample_data["service_list"]
    data[1][2] = True
    instance = CliTable(data)
    instance.stringify_boolean_cols(2)
    assert instance.PICTOGRAM_TRUE in instance.table.table_data[1]
    assert instance.PICTOGRAM_FALSE in instance.table.table_data[2]
