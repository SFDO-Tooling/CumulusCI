import io
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest import mock

import click
import pytest
import responses

from cumulusci.core.config import (
    BaseProjectConfig,
    OrgConfig,
    ScratchOrgConfig,
    ServiceConfig,
    UniversalConfig,
)
from cumulusci.core.config.sfdx_org_config import SfdxOrgConfig
from cumulusci.core.exceptions import (
    OrgNotFound,
    ScratchOrgException,
    ServiceNotConfigured,
)
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.core.tests.utils import MockLookup
from cumulusci.utils import parse_api_datetime

from .. import org
from .utils import run_cli_command, run_click_command


class TestOrgCommands:
    @mock.patch("webbrowser.open")
    def test_org_browser(self, browser_open):
        org_config = mock.Mock()
        runtime = mock.Mock()
        runtime.get_org.return_value = ("test", org_config)

        run_click_command(
            org.org_browser, runtime=runtime, org_name="test", path=None, url_only=False
        )

        org_config.refresh_oauth_token.assert_called_once()
        browser_open.assert_called_once()
        org_config.save.assert_called_once_with()

    @mock.patch("webbrowser.open")
    def test_org_browser_path(self, browser_open):
        start_url = "https://random-word-1234-dev-ed.cs42.my.salesforce.com//secur/frontdoor.jsp?sid=00Dorgid!longtoken"
        target_path = "/lightning/setup/Package/home"

        org_config = mock.Mock()
        org_config.start_url = start_url
        runtime = mock.Mock()
        runtime.get_org.return_value = ("test", org_config)

        run_click_command(
            org.org_browser,
            runtime=runtime,
            org_name="test",
            path=target_path,
            url_only=False,
        )

        org_config.refresh_oauth_token.assert_called_once()
        expected_query = "&retURL=%2Flightning%2Fsetup%2FPackage%2Fhome"
        browser_open.assert_called_once_with(start_url + expected_query)
        org_config.save.assert_called_once_with()

    @mock.patch("click.echo")
    @mock.patch("webbrowser.open")
    def test_org_browser_url_only(self, browser_open, click_echo):
        start_url = "https://random-word-1234-dev-ed.cs42.my.salesforce.com//secur/frontdoor.jsp?sid=00Dorgid!longtoken"
        org_config = mock.Mock()
        org_config.start_url = start_url
        runtime = mock.Mock()
        runtime.get_org.return_value = ("test", org_config)

        run_click_command(
            org.org_browser,
            runtime=runtime,
            org_name="test",
            path=None,
            url_only=True,
        )

        org_config.refresh_oauth_token.assert_called_once()
        browser_open.assert_not_called()
        click_echo.assert_called_once_with(start_url)
        org_config.save.assert_called_once_with()

    @mock.patch("cumulusci.oauth.client.OAuth2Client.auth_code_flow")
    @responses.activate
    def test_org_connect(self, auth_code_flow):
        auth_code_flow.return_value = {
            "instance_url": "https://instance",
            "access_token": "BOGUS",
            "id": "OODxxxxxxxxxxxx/user",
        }
        runtime = mock.Mock()
        runtime.project_config = BaseProjectConfig(UniversalConfig(), config={})
        runtime.keychain = BaseProjectKeychain(runtime.project_config, None)
        responses.add(
            method="GET",
            url="https://instance/services/oauth2/userinfo",
            body=b"{}",
            status=200,
        )
        responses.add(
            method="GET",
            url="https://instance/services/data/v45.0/sobjects/Organization/OODxxxxxxxxxxxx",
            json={
                "TrialExpirationDate": None,
                "OrganizationType": "Developer Edition",
                "IsSandbox": False,
                "InstanceName": "CS420",
                "NamespacePrefix": None,
            },
            status=200,
        )
        responses.add("GET", "https://instance/services/data", json=[{"version": 45.0}])

        result = run_cli_command("org", "connect", "test", "--default", runtime=runtime)

        name, org_config = runtime.keychain.get_default_org()
        assert name == "test"
        assert org_config.id == "OODxxxxxxxxxxxx/user"
        assert org_config.connected_app == "built-in"
        assert org_config.expires == "Persistent"
        assert "Connecting org using the built-in connected app..." in result.output
        assert "test is now the default org" in result.output

    @mock.patch("cumulusci.oauth.client.OAuth2Client.auth_code_flow")
    @responses.activate
    def test_org_connect__non_default_connected_app(self, auth_code_flow):
        auth_code_flow.return_value = {
            "instance_url": "https://instance",
            "access_token": "BOGUS",
            "id": "OODxxxxxxxxxxxx/user",
        }
        runtime = mock.Mock()
        runtime.project_config = BaseProjectConfig(UniversalConfig(), config={})
        runtime.keychain = BaseProjectKeychain(runtime.project_config, None)
        runtime.keychain.set_service(
            "connected_app",
            "other",
            ServiceConfig(
                {
                    "login_url": "https://other",
                    "callback_url": "http://localhost:8080/callback",
                    "client_id": "ID",
                    "client_secret": "SECRET",
                }
            ),
        )
        responses.add(
            method="GET",
            url="https://instance/services/oauth2/userinfo",
            body=b"{}",
            status=200,
        )
        responses.add(
            method="GET",
            url="https://instance/services/data/v45.0/sobjects/Organization/OODxxxxxxxxxxxx",
            json={
                "TrialExpirationDate": None,
                "OrganizationType": "Developer Edition",
                "IsSandbox": False,
                "InstanceName": "CS420",
                "NamespacePrefix": None,
            },
            status=200,
        )
        responses.add("GET", "https://instance/services/data", json=[{"version": 45.0}])

        result = run_cli_command(
            "org", "connect", "test", "--connected_app", "other", runtime=runtime
        )

        org_config = runtime.keychain.get_org("test")
        assert org_config.connected_app == "other"
        assert "Connecting org using the other connected app..." in result.output

    @mock.patch("cumulusci.cli.org.connect_org_to_keychain")
    def test_org_connect__sandbox(self, connect_to_keychain):
        mocked_connected_app = mock.Mock()
        mocked_connected_app.client_id = "foo"
        mocked_connected_app.client_secret = "bar"
        mocked_connected_app.callback_url = "https://foo.bar.baz/"

        runtime = mock.Mock()
        runtime.keychain.get_service.return_value = mocked_connected_app

        run_cli_command("org", "connect", "blah", "--sandbox", runtime=runtime)

        actual_client_config = connect_to_keychain.call_args_list[0][0][0].client_config
        assert actual_client_config.auth_uri.startswith("https://test.salesforce.com/")
        assert actual_client_config.token_uri.startswith("https://test.salesforce.com/")

    @mock.patch("cumulusci.cli.org.connect_org_to_keychain")
    def test_org_connect__prod_default(self, connect_to_keychain):
        runtime = mock.Mock()
        runtime.project_config = BaseProjectConfig(UniversalConfig(), config={})
        runtime.keychain = BaseProjectKeychain(runtime.project_config, None)

        run_cli_command("org", "connect", "blah", runtime=runtime)

        actual_client_config = connect_to_keychain.call_args_list[0][0][0].client_config
        assert actual_client_config.auth_uri.startswith("https://login.salesforce.com/")
        assert actual_client_config.token_uri.startswith(
            "https://login.salesforce.com/"
        )

    @mock.patch("cumulusci.cli.org.connect_org_to_keychain")
    def test_org_connect__other_connected_app_login_url(self, connect_to_keychain):
        runtime = mock.Mock()
        runtime.project_config = BaseProjectConfig(UniversalConfig(), config={})
        runtime.keychain = BaseProjectKeychain(runtime.project_config, None)
        runtime.keychain.set_service(
            "connected_app",
            "other",
            ServiceConfig(
                {
                    "client_id": "foo",
                    "client_secret": "bar",
                    "callback_url": "https://foo.bar.baz/",
                    "login_url": "https://other",
                }
            ),
        )

        run_cli_command(
            "org", "connect", "blah", "--connected-app", "other", runtime=runtime
        )

        actual_client_config = connect_to_keychain.call_args_list[0][0][0].client_config
        assert actual_client_config.auth_uri.startswith("https://other/")
        assert actual_client_config.token_uri.startswith("https://other/")

    @mock.patch("cumulusci.cli.org.connect_org_to_keychain")
    def test_org_connect__login_url_from_cli_option(self, connect_to_keychain):
        runtime = mock.Mock()
        runtime.project_config = BaseProjectConfig(UniversalConfig(), config={})
        runtime.keychain = BaseProjectKeychain(runtime.project_config, None)

        run_cli_command(
            "org", "connect", "blah", "--login-url", "https://custom", runtime=runtime
        )

        actual_client_config = connect_to_keychain.call_args_list[0][0][0].client_config
        assert actual_client_config.auth_uri.startswith("https://custom/")
        assert actual_client_config.token_uri.startswith("https://custom/")

    def test_org_connect__bad_connected_app_name(self):
        runtime = mock.Mock()
        runtime.project_config = BaseProjectConfig(UniversalConfig(), config={})
        runtime.keychain = BaseProjectKeychain(runtime.project_config, None)

        with pytest.raises(
            ServiceNotConfigured,
            match="No service of type connected_app configured with name: bogus",
        ):
            run_cli_command(
                "org", "connect", "blah", "--connected-app", "bogus", runtime=runtime
            )

    @mock.patch("cumulusci.cli.org.OAuth2Client")
    @responses.activate
    def test_org_connect_expires(self, oauth2client):
        client_instance = mock.Mock()
        client_instance.auth_code_flow.return_value = {
            "instance_url": "https://instance",
            "access_token": "BOGUS",
            "id": "OODxxxxxxxxxxxx/user",
        }
        oauth2client.return_value = client_instance
        runtime = mock.Mock()
        runtime.keychain.get_service.return_value = mock.Mock(
            client_id="asdfasdf",
            client_secret="asdfasdf",
            callback_url="http://localhost:8080/callback",
        )
        responses.add(
            method="GET",
            url="https://instance/services/oauth2/userinfo",
            body=b"{}",
            status=200,
        )
        responses.add(
            method="GET",
            url="https://instance/services/data/v45.0/sobjects/Organization/OODxxxxxxxxxxxx",
            json={
                "TrialExpirationDate": "1970-01-01T12:34:56.000+0000",
                "OrganizationType": "Developer Edition",
                "IsSandbox": True,
                "InstanceName": "CS420",
                "NamespacePrefix": None,
            },
            status=200,
        )
        responses.add("GET", "https://instance/services/data", json=[{"version": 45.0}])

        run_click_command(
            org.org_connect,
            runtime=runtime,
            org_name="test",
            sandbox=True,
            login_url=None,
            default=True,
            global_org=False,
        )

        runtime.check_org_overwrite.assert_called_once()
        runtime.keychain.set_org.assert_called_once()
        org_config = runtime.keychain.set_org.call_args[0][0]
        assert org_config.expires == date(1970, 1, 1)
        runtime.keychain.set_default_org.assert_called_once_with("test")

    def test_org_connect_connected_app_not_configured(self):
        runtime = mock.Mock()
        runtime.keychain.get_service.side_effect = ServiceNotConfigured

        with pytest.raises(ServiceNotConfigured):
            run_click_command(
                org.org_connect,
                runtime=runtime,
                org_name="test",
                sandbox=True,
                login_url=None,
                default=True,
                global_org=False,
            )

    def test_org_connect_lightning_url(self):
        runtime = mock.Mock()

        with pytest.raises(click.UsageError, match="lightning"):
            run_click_command(
                org.org_connect,
                runtime=runtime,
                org_name="test",
                sandbox=True,
                login_url="https://test1.lightning.force.com/",
                default=True,
                global_org=False,
            )

    def test_org_default(self):
        runtime = mock.Mock()

        run_click_command(
            org.org_default, runtime=runtime, org_name="test", unset=False
        )

        runtime.keychain.set_default_org.assert_called_once_with("test")

    def test_org_default_unset(self):
        runtime = mock.Mock()

        run_click_command(org.org_default, runtime=runtime, org_name="test", unset=True)

        runtime.keychain.unset_default_org.assert_called_once()

    @mock.patch("sarge.Command")
    def test_org_import(self, cmd):
        runtime = mock.Mock()
        result = b"""{
            "result": {
                "createdDate": "1970-01-01T00:00:00.000Z",
                "expirationDate": "1970-01-01",
                "instanceUrl": "url",
                "accessToken": "OODxxxxxxxxxxxx!token",
                "username": "test@test.org",
                "password": "password"
            }
        }"""
        cmd.return_value = mock.Mock(
            stderr=io.BytesIO(b""), stdout=io.BytesIO(result), returncode=0
        )

        out = []
        with mock.patch("click.echo", out.append):
            run_click_command(
                org.org_import,
                username_or_alias="test@test.org",
                org_name="test",
                runtime=runtime,
            )
            runtime.keychain.set_org.assert_called_once()
        assert (
            "Imported scratch org: OODxxxxxxxxxxxx, username: test@test.org"
            in "".join(out)
        )

    @mock.patch("sarge.Command")
    @responses.activate
    def test_org_import__persistent_org(self, cmd):
        runtime = mock.Mock()
        result = b"""{
            "result": {
                "id": "OODxxxxxxxxxxxx",
                "createdDate": null,
                "instanceUrl": "https://instance",
                "accessToken": "OODxxxxxxxxxxxx!token",
                "username": "test@test.org",
                "password": "password"
            }
        }"""
        cmd.return_value = mock.Mock(
            stderr=io.BytesIO(b""), stdout=io.BytesIO(result), returncode=0
        )

        # Mock the call to get the Organization sObject
        responses.add(
            method="GET",
            url="https://instance/services/data",
            status=200,
            json=[{"version": "54.0"}],
        )
        responses.add(
            method="GET",
            url="https://instance/services/data/v54.0/sobjects/Organization/OODxxxxxxxxxxxx",
            json={
                "TrialExpirationDate": None,
                "OrganizationType": "Developer Edition",
                "IsSandbox": True,
                "InstanceName": "CS420",
                "NamespacePrefix": None,
            },
            status=200,
        )

        out = []
        with mock.patch("click.echo", out.append):
            run_click_command(
                org.org_import,
                username_or_alias="test@test.org",
                org_name="test",
                runtime=runtime,
            )
            runtime.keychain.set_org.assert_called_once()
            created_org = runtime.keychain.set_org.call_args[0][0]
            assert isinstance(created_org, SfdxOrgConfig)
            assert created_org.config["sfdx"]
        assert created_org.config["expires"] == "Persistent"

        assert "Imported org: OODxxxxxxxxxxxx, username: test@test.org" in "".join(out)

    @mock.patch("sarge.Command")
    @responses.activate
    def test_org_import__trial_org(self, cmd):
        runtime = mock.Mock()
        result = b"""{
            "result": {
                "id": "OODxxxxxxxxxxxx",
                "createdDate": null,
                "instanceUrl": "https://instance",
                "accessToken": "OODxxxxxxxxxxxx!token",
                "username": "test@test.org",
                "password": "password"
            }
        }"""
        cmd.return_value = mock.Mock(
            stderr=io.BytesIO(b""), stdout=io.BytesIO(result), returncode=0
        )

        # Mock the call to get the Organization sObject
        api_datetime = "2030-08-07T16:00:56.000+0000"
        responses.add(
            method="GET",
            url="https://instance/services/data",
            status=200,
            json=[{"version": "54.0"}],
        )
        responses.add(
            method="GET",
            url="https://instance/services/data/v54.0/sobjects/Organization/OODxxxxxxxxxxxx",
            json={
                "TrialExpirationDate": api_datetime,
                "OrganizationType": "Developer Edition",
                "IsSandbox": True,
                "InstanceName": "CS420",
                "NamespacePrefix": None,
            },
            status=200,
        )

        out = []
        with mock.patch("click.echo", out.append):
            run_click_command(
                org.org_import,
                username_or_alias="test@test.org",
                org_name="test",
                runtime=runtime,
            )
            runtime.keychain.set_org.assert_called_once()
            created_org = runtime.keychain.set_org.call_args[0][0]
            assert isinstance(created_org, SfdxOrgConfig)
            assert created_org.config["sfdx"]
            assert (
                created_org.config["expires"] == parse_api_datetime(api_datetime).date()
            )

        assert "Imported org: OODxxxxxxxxxxxx, username: test@test.org" in "".join(out)

    def test_calculate_org_days(self):
        info_1 = {
            "created_date": "1970-01-01T12:34:56.789Z",
            "expiration_date": "1970-01-02",
        }
        actual_days = org.calculate_org_days(info_1)
        assert 1 == actual_days

        info_7 = {
            "created_date": "1970-01-01T12:34:56.789+0000",
            "expiration_date": "1970-01-08",
        }
        actual_days = org.calculate_org_days(info_7)
        assert 7 == actual_days

        info_14 = {
            "created_date": "1970-01-01T12:34:56.000+0000",
            "expiration_date": "1970-01-15",
        }
        actual_days = org.calculate_org_days(info_14)
        assert 14 == actual_days

        info_bad__no_created_date = {"expiration_date": "1970-01-15"}
        actual_days = org.calculate_org_days(info_bad__no_created_date)
        assert 1 == actual_days

        info_bad__no_expiration_date = {"created_date": "1970-01-01T12:34:56.000+0000"}
        actual_days = org.calculate_org_days(info_bad__no_expiration_date)
        assert 1 == actual_days

    def test_org_info(self):
        org_config = mock.Mock()
        org_config.config = {
            "days": 1,
            "default": True,
            "password": None,
            "connected_app": "built-in",
        }
        org_config.expires = date.today()
        org_config.latest_api_version = "42.0"
        runtime = mock.Mock()
        runtime.get_org.return_value = ("test", org_config)

        with mock.patch("cumulusci.cli.org.CliTable") as cli_tbl:
            run_click_command(
                org.org_info, runtime=runtime, org_name="test", print_json=False
            )
            cli_tbl.assert_called_with(
                [
                    ["Org: test", ""],
                    ["\x1b[1mapi_version\x1b[0m", "42.0"],
                    ["\x1b[1mconnected_app\x1b[0m", "built-in"],
                    ["\x1b[1mdays\x1b[0m", "1"],
                    ["\x1b[1mdefault\x1b[0m", "True"],
                    ["\x1b[1mpassword\x1b[0m", "None"],
                ],
            )

        org_config.save.assert_called_once_with()

    def test_org_info_json(self, capsys):
        class Unserializable(object):
            def __str__(self):
                return "<unserializable>"

        org_config = mock.Mock()
        org_config.config = {"test": "test", "unserializable": Unserializable()}
        org_config.expires = date.today()
        runtime = mock.Mock()
        runtime.get_org.return_value = ("test", org_config)

        run_click_command(
            org.org_info, runtime=runtime, org_name="test", print_json=True
        )

        org_config.refresh_oauth_token.assert_called_once()
        captured = capsys.readouterr()
        assert (
            captured.out
            == '{\n    "test": "test",\n    "unserializable": "<unserializable>"\n}\n'
        )
        org_config.save.assert_called_once_with()

    @mock.patch("cumulusci.cli.org.CliTable")
    def test_org_list(self, cli_tbl):
        runtime = mock.Mock()
        runtime.universal_config.cli__plain_output = None
        org_configs = {
            "test0": ScratchOrgConfig(
                {
                    "default": True,
                    "scratch": True,
                    "date_created": datetime.now() - timedelta(days=8),
                    "days": 7,
                    "config_name": "dev",
                    "username": "test0@example.com",
                },
                "test0",
            ),
            "test1": ScratchOrgConfig(
                {
                    "default": False,
                    "scratch": True,
                    "date_created": datetime.now(),
                    "days": 7,
                    "config_name": "dev",
                    "username": "test1@example.com",
                    "instance_url": "https://sneaky-master-2330-dev-ed.cs22.my.salesforce.com",
                },
                "test1",
            ),
            "test2": OrgConfig(
                {
                    "default": False,
                    "scratch": False,
                    "expires": "Persistent",
                    "expired": False,
                    "config_name": "dev",
                    "username": "test2@example.com",
                    "instance_url": "https://dude-chillin-2330-dev-ed.cs22.my.salesforce.com",
                },
                "test2",
            ),
            "test3": OrgConfig(
                {
                    "default": False,
                    "scratch": False,
                    "expires": "2019-11-19",
                    "expired": False,
                    "config_name": "dev",
                    "username": "test3@example.com",
                    "instance_url": "https://dude-chillin-2330-dev-ed.cs22.my.salesforce.com",
                },
                "test3",
            ),
            "test4": OrgConfig(
                {
                    "default": False,
                    "scratch": False,
                    "expired": False,
                    "config_name": "dev",
                    "username": "test4@example.com",
                    "instance_url": "https://dude-chillin-2330-dev-ed.cs22.my.salesforce.com",
                },
                "test4",
            ),
            "test5": OrgConfig(
                {
                    "default": False,
                    "scratch": True,
                    "expires": "2019-11-19",
                    "expired": False,
                    "config_name": "dev",
                    "username": "test5@example.com",
                    "instance_url": "https://dude-chillin-2330-dev-ed.cs22.my.salesforce.com",
                },
                "test5",
            ),
            "test6": OrgConfig(
                {
                    "default": False,
                    "scratch": True,
                    "expired": False,
                    "config_name": "dev",
                    "username": "test6@example.com",
                    "instance_url": "https://dude-chillin-2330-dev-ed.cs22.my.salesforce.com",
                },
                "test6",
            ),
        }

        runtime.keychain.list_orgs.return_value = list(org_configs.keys())
        runtime.keychain.get_org = lambda orgname: org_configs[orgname]
        runtime.project_config.cache_dir = Path("does_not_possibly_exist")

        runtime.keychain.get_default_org.return_value = (
            "test0",
            ScratchOrgConfig(
                {
                    "default": True,
                    "scratch": True,
                    "date_created": datetime.now() - timedelta(days=8),
                    "days": 7,
                    "config_name": "dev",
                    "username": "test0@example.com",
                },
                "test0",
            ),
        )

        run_click_command(org.org_list, runtime=runtime, json_flag=False, plain=False)

        scratch_table_call = mock.call(
            [
                ["Default", "Name", "Days", "Expired", "Config", "Domain"],
                [True, "test0", "7", True, "dev", ""],
                [False, "test1", "1/7", False, "dev", "sneaky-master-2330-dev-ed.cs22"],
            ],
            title="Scratch Orgs",
            dim_rows=[0, 1],
        )
        connected_table_call = mock.call(
            [
                ["Default", "Name", "Username", "Expires"],
                [False, "test2", "test2@example.com", "Persistent"],
                [False, "test3", "test3@example.com", "2019-11-19"],
                [False, "test4", "test4@example.com", "Unknown"],
                [False, "test5", "test5@example.com", "2019-11-19"],
                [False, "test6", "test6@example.com", "Unknown"],
            ],
            title="Connected Orgs",
        )

        assert scratch_table_call in cli_tbl.call_args_list
        assert connected_table_call in cli_tbl.call_args_list
        runtime.keychain.cleanup_org_cache_dirs.assert_called_once()

    @mock.patch("cumulusci.cli.org.click.echo")
    def test_org_list__json(self, echo):
        runtime = mock.Mock()
        runtime.universal_config.cli__plain_output = None
        org_configs = {
            "test0": ScratchOrgConfig(
                {
                    "default": True,
                    "scratch": True,
                    "date_created": datetime.now() - timedelta(days=8),
                    "days": 7,
                    "config_name": "dev",
                    "username": "test0@example.com",
                },
                "test0",
            ),
            "test1": ScratchOrgConfig(
                {
                    "default": False,
                    "scratch": True,
                    "date_created": datetime.now(),
                    "days": 7,
                    "config_name": "dev",
                    "username": "test1@example.com",
                    "instance_url": "https://sneaky-master-2330-dev-ed.cs22.my.salesforce.com",
                },
                "test1",
            ),
            "test2": OrgConfig(
                {
                    "default": False,
                    "scratch": False,
                    "expires": "Persistent",
                    "expired": False,
                    "config_name": "dev",
                    "username": "test2@example.com",
                    "instance_url": "https://dude-chillin-2330-dev-ed.cs22.my.salesforce.com",
                },
                "test2",
            ),
        }

        runtime.keychain.list_orgs.return_value = list(org_configs.keys())
        runtime.keychain.get_org = lambda orgname: org_configs[orgname]
        runtime.project_config.cache_dir = Path("does_not_possibly_exist")

        runtime.keychain.get_default_org.return_value = (
            "test0",
            ScratchOrgConfig(
                {
                    "default": True,
                    "scratch": True,
                    "date_created": datetime.now() - timedelta(days=8),
                    "days": 7,
                    "config_name": "dev",
                    "username": "test0@example.com",
                },
                "test0",
            ),
        )

        run_click_command(org.org_list, runtime=runtime, json_flag=True, plain=False)
        expected = {
            "test0": {
                "is_default": True,
                "name": "test0",
                "days": "7",
                "expired": True,
                "config": "dev",
                "domain": "",
                "is_scratch": True,
            },
            "test1": {
                "is_default": False,
                "name": "test1",
                "days": "1/7",
                "expired": False,
                "config": "dev",
                "domain": "sneaky-master-2330-dev-ed.cs22",
                "is_scratch": True,
            },
            "test2": {
                "is_default": False,
                "name": "test2",
                "username": "test2@example.com",
                "expires": "Persistent",
                "is_scratch": False,
            },
        }

        echo.assert_called_once_with(json.dumps(expected))

    @mock.patch("click.echo")
    @mock.patch("cumulusci.cli.org.CliTable")
    def test_org_list__error(self, cli_tbl, echo):
        runtime = mock.Mock()
        runtime.universal_config.cli__plain_output = None
        org_configs = {
            "test0": ScratchOrgConfig(
                {
                    "default": True,
                    "scratch": True,
                    "date_created": datetime.now() - timedelta(days=8),
                    "days": 7,
                    "config_name": "dev",
                    "username": "test0@example.com",
                },
                "test0",
            ),
            "test1": AssertionError("NOPE!"),
            "test2": OrgConfig(
                {
                    "default": False,
                    "scratch": False,
                    "expires": "Persistent",
                    "expired": False,
                    "config_name": "dev",
                    "username": "test2@example.com",
                    "instance_url": "https://dude-chillin-2330-dev-ed.cs22.my.salesforce.com",
                },
                "test2",
            ),
        }

        runtime.keychain.list_orgs.return_value = list(org_configs.keys())

        def get_org(orgname):
            value = org_configs[orgname]
            if isinstance(value, Exception):
                raise value
            return value

        runtime.keychain.get_org = get_org
        runtime.project_config.cache_dir = Path("does_not_possibly_exist")
        runtime.keychain.cleanup_org_cache_dirs.side_effect = AssertionError("OUCH!")

        runtime.keychain.get_default_org.return_value = (
            "test0",
            ScratchOrgConfig(
                {
                    "default": True,
                    "scratch": True,
                    "date_created": datetime.now() - timedelta(days=8),
                    "days": 7,
                    "config_name": "dev",
                    "username": "test0@example.com",
                },
                "test0",
            ),
        )

        run_click_command(org.org_list, runtime=runtime, json_flag=False, plain=False)

        assert "Cannot load org config for `test1`" in str(
            echo.mock_calls
        ), echo.mock_calls
        assert "NOPE!" in str(echo.mock_calls), echo.mock_calls
        assert "Cannot cleanup org cache dirs" in str(echo.mock_calls), echo.mock_calls

    @mock.patch("click.echo")
    def test_org_prune(self, echo):
        runtime = mock.Mock()
        runtime.keychain.list_orgs.return_value = [
            "shape1",
            "shape2",
            "remove1",
            "remove2",
            "active1",
            "active2",
            "persistent",
        ]

        runtime.project_config.lookup = MockLookup(
            orgs__scratch={
                "shape1": True,
                "shape2": True,
            },
        )

        runtime.keychain.get_org.side_effect = [
            ScratchOrgConfig(
                {
                    "default": True,
                    "scratch": True,
                    "date_created": datetime.now() - timedelta(days=8),
                    "days": 7,
                    "config_name": "dev",
                    "username": "test0@example.com",
                },
                "shape1",
            ),
            ScratchOrgConfig(
                {
                    "default": False,
                    "scratch": True,
                    "date_created": datetime.now(),
                    "days": 7,
                    "config_name": "dev",
                    "username": "test1@example.com",
                },
                "shape2",
            ),
            ScratchOrgConfig(
                {
                    "default": False,
                    "scratch": True,
                    "date_created": datetime(1999, 11, 1),
                    "days": 7,
                    "config_name": "dev",
                    "username": "remove1@example.com",
                },
                "remove1",
            ),
            ScratchOrgConfig(
                {
                    "default": False,
                    "scratch": True,
                    "date_created": datetime(1999, 11, 1),
                    "days": 7,
                    "config_name": "dev",
                    "username": "remove2@example.com",
                },
                "remove2",
            ),
            ScratchOrgConfig(
                {
                    "default": False,
                    "scratch": True,
                    "date_created": datetime.now() - timedelta(days=1),
                    "days": 7,
                    "config_name": "dev",
                    "username": "active1@example.com",
                },
                "active1",
            ),
            ScratchOrgConfig(
                {
                    "default": False,
                    "scratch": True,
                    "date_created": datetime.now() - timedelta(days=1),
                    "days": 7,
                    "config_name": "dev",
                    "username": "active2@example.com",
                },
                "active2",
            ),
            OrgConfig(
                {
                    "default": False,
                    "scratch": False,
                    "expires": "Persistent",
                    "expired": False,
                    "config_name": "dev",
                    "username": "persistent@example.com",
                    "instance_url": "https://dude-chillin-2330-dev-ed.cs22.my.salesforce.com",
                },
                "persistent",
            ),
        ]

        run_click_command(org.org_prune, runtime=runtime, include_active=False)

        echo.assert_any_call(
            "Successfully removed 2 expired scratch orgs: remove1, remove2"
        )
        echo.assert_any_call("Skipped org shapes: shape1, shape2")
        echo.assert_any_call("Skipped active orgs: active1, active2")

        runtime.keychain.remove_org.assert_has_calls(
            [mock.call("remove1"), mock.call("remove2")]
        )
        assert runtime.keychain.remove_org.call_count == 2

    @mock.patch("click.echo")
    def test_org_prune_no_expired(self, echo):
        runtime = mock.Mock()
        runtime.keychain.list_orgs.return_value = [
            "shape1",
            "shape2",
            "active1",
            "active2",
            "persistent",
        ]

        runtime.project_config.lookup = MockLookup(
            orgs__scratch={
                "shape1": True,
                "shape2": True,
            }
        )

        runtime.keychain.get_org.side_effect = [
            ScratchOrgConfig(
                {
                    "default": True,
                    "scratch": True,
                    "date_created": datetime.now() - timedelta(days=8),
                    "days": 7,
                    "config_name": "dev",
                    "username": "test0@example.com",
                },
                "shape1",
            ),
            ScratchOrgConfig(
                {
                    "default": False,
                    "scratch": True,
                    "date_created": datetime.now(),
                    "days": 7,
                    "config_name": "dev",
                    "username": "test1@example.com",
                },
                "shape2",
            ),
            ScratchOrgConfig(
                {
                    "default": False,
                    "scratch": True,
                    "date_created": datetime.now() - timedelta(days=1),
                    "days": 7,
                    "config_name": "dev",
                    "username": "active1@example.com",
                },
                "active1",
            ),
            ScratchOrgConfig(
                {
                    "default": False,
                    "scratch": True,
                    "date_created": datetime.now() - timedelta(days=1),
                    "days": 7,
                    "config_name": "dev",
                    "username": "active2@example.com",
                },
                "active2",
            ),
            OrgConfig(
                {
                    "default": False,
                    "scratch": False,
                    "expires": "Persistent",
                    "expired": False,
                    "config_name": "dev",
                    "username": "persistent@example.com",
                    "instance_url": "https://dude-chillin-2330-dev-ed.cs22.my.salesforce.com",
                },
                "persistent",
            ),
        ]

        run_click_command(org.org_prune, runtime=runtime, include_active=False)
        runtime.keychain.remove_org.assert_not_called()

        echo.assert_any_call("No expired scratch orgs to delete. ✨")

    @mock.patch("click.echo")
    def test_org_prune_include_active(self, echo):
        runtime = mock.Mock()
        runtime.keychain.list_orgs.return_value = [
            "shape1",
            "shape2",
            "remove1",
            "remove2",
            "active1",
            "active2",
            "persistent",
        ]

        def lookup(name, default):
            assert name == "orgs__scratch", name
            return {"shape1": True, "shape2": True}

        runtime.project_config.lookup = lookup

        runtime.keychain.get_org.side_effect = [
            ScratchOrgConfig(
                {
                    "default": True,
                    "scratch": True,
                    "days": 7,
                    "config_name": "dev",
                    "username": "test0@example.com",
                },
                "shape1",
            ),
            ScratchOrgConfig(
                {
                    "default": False,
                    "scratch": True,
                    "days": 7,
                    "config_name": "dev",
                    "username": "test1@example.com",
                },
                "shape2",
            ),
            ScratchOrgConfig(
                {
                    "default": False,
                    "scratch": True,
                    "date_created": datetime(1999, 11, 1),
                    "days": 7,
                    "config_name": "dev",
                    "username": "remove1@example.com",
                },
                "remove1",
            ),
            ScratchOrgConfig(
                {
                    "default": False,
                    "scratch": True,
                    "date_created": datetime(1999, 11, 1),
                    "days": 7,
                    "config_name": "dev",
                    "username": "remove2@example.com",
                },
                "remove2",
            ),
            ScratchOrgConfig(
                {
                    "default": False,
                    "scratch": True,
                    "date_created": datetime.now() - timedelta(days=1),
                    "days": 7,
                    "config_name": "dev",
                    "username": "active1@example.com",
                },
                "active1",
            ),
            ScratchOrgConfig(
                {
                    "default": False,
                    "scratch": True,
                    "date_created": datetime.now() - timedelta(days=1),
                    "days": 7,
                    "config_name": "dev",
                    "username": "active2@example.com",
                },
                "active2",
            ),
            OrgConfig(
                {
                    "default": False,
                    "scratch": False,
                    "expires": "Persistent",
                    "expired": False,
                    "config_name": "dev",
                    "username": "persistent@example.com",
                    "instance_url": "https://dude-chillin-2330-dev-ed.cs22.my.salesforce.com",
                },
                "persistent",
            ),
        ]

        run_click_command(org.org_prune, runtime=runtime, include_active=True)

        echo.assert_any_call(
            "Successfully removed 2 expired scratch orgs: remove1, remove2"
        )
        echo.assert_any_call(
            "Successfully removed 2 active scratch orgs: active1, active2"
        )
        echo.assert_any_call("Skipped org shapes: shape1, shape2")

        runtime.keychain.remove_org.assert_has_calls(
            [
                mock.call("remove1"),
                mock.call("remove2"),
                mock.call("active1"),
                mock.call("active2"),
            ]
        )
        assert runtime.keychain.remove_org.call_count == 4

    def test_org_remove(self):
        org_config = mock.Mock()
        org_config.can_delete.return_value = True
        runtime = mock.Mock()
        runtime.keychain.get_org.return_value = org_config

        run_click_command(
            org.org_remove, runtime=runtime, org_name="test", global_org=False
        )

        org_config.delete_org.assert_called_once()
        runtime.keychain.remove_org.assert_called_once_with("test", False)

    @mock.patch("click.echo")
    def test_org_remove_delete_error(self, echo):
        org_config = mock.Mock()
        org_config.can_delete.return_value = True
        org_config.delete_org.side_effect = Exception
        runtime = mock.Mock()
        runtime.keychain.get_org.return_value = org_config

        run_click_command(
            org.org_remove, runtime=runtime, org_name="test", global_org=False
        )

        echo.assert_any_call("Removing org regardless.")

    def test_org_remove_not_found(self):
        runtime = mock.Mock()
        runtime.keychain.get_org.side_effect = OrgNotFound

        with pytest.raises(
            click.ClickException, match="Org test does not exist in the keychain"
        ):
            run_click_command(
                org.org_remove, runtime=runtime, org_name="test", global_org=False
            )

    def test_org_scratch(self):
        runtime = mock.Mock()

        runtime.project_config.lookup = MockLookup(
            orgs__scratch={"dev": {"orgName": "Dev"}}
        )

        run_click_command(
            org.org_scratch,
            runtime=runtime,
            config_name="dev",
            org_name="test",
            default=True,
            devhub="hub",
            days=7,
            no_password=True,
        )

        runtime.check_org_overwrite.assert_called_once()
        runtime.keychain.create_scratch_org.assert_called_with(
            "test", "dev", 7, set_password=False
        )
        runtime.keychain.set_default_org.assert_called_with("test")

    def test_org_scratch__not_default(self):
        runtime = mock.Mock()
        runtime.project_config.lookup = MockLookup(
            orgs__scratch={"dev": {"orgName": "Dev"}}
        )

        run_click_command(
            org.org_scratch,
            runtime=runtime,
            config_name="dev",
            org_name="test",
            default=False,
            devhub="hub",
            days=7,
            no_password=True,
        )

        runtime.check_org_overwrite.assert_called_once()
        runtime.keychain.create_scratch_org.assert_called_with(
            "test", "dev", 7, set_password=False
        )

    def test_org_scratch_no_configs(self):
        runtime = mock.Mock()
        runtime.project_config.lookup = MockLookup(orgs__scratch=None)

        with pytest.raises(click.UsageError):
            run_click_command(
                org.org_scratch,
                runtime=runtime,
                config_name="dev",
                org_name="test",
                default=True,
                devhub="hub",
                days=7,
                no_password=True,
            )

    def test_org_scratch_config_not_found(self):
        runtime = mock.Mock()
        runtime.project_config.lookup = MockLookup(orgs__scratch={"bogus": {}})

        with pytest.raises(click.UsageError):
            run_click_command(
                org.org_scratch,
                runtime=runtime,
                config_name="dev",
                org_name="test",
                default=True,
                devhub="hub",
                days=7,
                no_password=True,
            )

    def test_org_scratch_delete(self):
        org_config = mock.Mock()
        runtime = mock.Mock()
        runtime.keychain.get_org.return_value = org_config

        run_click_command(org.org_scratch_delete, runtime=runtime, org_name="test")

        org_config.delete_org.assert_called_once()
        org_config.save.assert_called_once_with()

    def test_org_scratch_delete_not_scratch(self):
        org_config = mock.Mock(scratch=False)
        runtime = mock.Mock()
        runtime.keychain.get_org.return_value = org_config

        with pytest.raises(click.UsageError):
            run_click_command(org.org_scratch_delete, runtime=runtime, org_name="test")

    @mock.patch("click.echo")
    def test_org_scratch_delete_error(self, echo):
        org_config = mock.Mock()
        org_config.delete_org.side_effect = ScratchOrgException
        runtime = mock.Mock()
        runtime.keychain.get_org.return_value = org_config
        run_click_command(org.org_scratch_delete, runtime=runtime, org_name="test")
        assert "org remove" in str(echo.mock_calls)

    @mock.patch("cumulusci.cli.org.get_simple_salesforce_connection")
    @mock.patch("code.interact")
    def test_org_shell(self, mock_code, mock_sf):
        org_config = mock.Mock()
        org_config.instance_url = "https://salesforce.com"
        org_config.access_token = "TEST"
        runtime = mock.Mock()
        runtime.get_org.return_value = ("test", org_config)

        run_click_command(org.org_shell, runtime=runtime, org_name="test")

        org_config.refresh_oauth_token.assert_called_once()
        mock_sf.assert_any_call(runtime.project_config, org_config)
        mock_sf.assert_any_call(runtime.project_config, org_config, base_url="tooling")
        org_config.save.assert_called_once_with()

        mock_code.assert_called_once()
        assert "sf" in mock_code.call_args[1]["local"]
        assert "tooling" in mock_code.call_args[1]["local"]

    @mock.patch("runpy.run_path")
    def test_org_shell_script(self, runpy):
        org_config = mock.Mock()
        org_config.instance_url = "https://salesforce.com"
        org_config.access_token = "TEST"
        runtime = mock.Mock()
        runtime.get_org.return_value = ("test", org_config)
        run_click_command(
            org.org_shell, runtime=runtime, org_name="test", script="foo.py"
        )
        runpy.assert_called_once()
        assert "sf" in runpy.call_args[1]["init_globals"]
        assert runpy.call_args[0][0] == "foo.py", runpy.call_args[0]

    @mock.patch("cumulusci.cli.ui.SimpleSalesforceUIHelpers.describe")
    def test_org_shell_describe(self, describe):
        org_config = mock.Mock()
        org_config.instance_url = "https://salesforce.com"
        org_config.access_token = "TEST"
        runtime = mock.Mock()
        runtime.get_org.return_value = ("test", org_config)
        run_click_command(
            org.org_shell, runtime=runtime, org_name="test", python="describe('blah')"
        )
        describe.assert_called_once()
        assert "blah" in describe.call_args[0][0]

    @mock.patch("cumulusci.cli.org.print")
    def test_org_shell_mutually_exclusive_args(self, print):
        org_config = mock.Mock()
        org_config.instance_url = "https://salesforce.com"
        org_config.access_token = "TEST"
        runtime = mock.Mock()
        runtime.get_org.return_value = ("test", org_config)
        with pytest.raises(Exception, match="Cannot specify both"):
            run_click_command(
                org.org_shell,
                runtime=runtime,
                org_name="foo",
                script="foo.py",
                python="print(config, runtime)",
            )
