import os
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from pydantic.v1 import ValidationError

from cumulusci.utils import temporary_dir
from cumulusci.utils.yaml.cumulusci_yml import (
    GitHubSourceModel,
    _validate_files,
    _validate_url,
    cci_safe_load,
    parse_from_yaml,
)


class TestCumulusciYml:
    def test_cumulusci_yaml(self):
        cciyml = parse_from_yaml("cumulusci.yml")
        assert cciyml.project.package.name == "CumulusCI"
        assert cciyml["project"]["package"]["name"] == "CumulusCI"
        assert (
            cciyml.tasks["robot"].options["suites"]
            == cciyml["tasks"]["robot"]["options"]["suites"]
            == "cumulusci/robotframework/tests"
        )

    def test_cumulusci_cumulusci_yaml(self, cumulusci_test_repo_root):
        cciyml = parse_from_yaml(cumulusci_test_repo_root / "cumulusci/cumulusci.yml")
        assert cciyml.tasks["connected_app"].options["overwrite"] is False

    def test_parse_cumulusci_yaml(self):
        yaml = """xyz:
                    y: abc"""
        lf = Mock()
        cciyml = cci_safe_load(StringIO(yaml), "foo", on_error=lf)
        assert isinstance(cciyml, dict)  # should parse despite model errors
        lf.assert_called()
        assert "foo" in str(lf.mock_calls[0][1][0])
        assert "xyz" in str(lf.mock_calls[0][1][0])

    @patch("cumulusci.utils.yaml.cumulusci_yml.validate_data")
    def test_unexpected_exceptions(self, validate_data):
        validate_data.side_effect = AssertionError("Boom!")
        yaml = """xyz:
            y: abc"""
        logfunc = Mock()
        cciyml = cci_safe_load(StringIO(yaml), "foo", on_error=logfunc)

        assert isinstance(cciyml, dict)  # should parse despite model errors
        logfunc.assert_called()
        validate_data.assert_called()

    @pytest.mark.large_vcr()
    def test_from_web(self):
        good_urls = """
            https://raw.githubusercontent.com/SalesforceFoundation/NPSP/master/cumulusci.yml
            https://raw.githubusercontent.com/SalesforceFoundation/EDA/master/cumulusci.yml
        """

        bad_urls = """
            https://raw.githubusercontent.com/SFDO-Tooling/CumulusCI-Test/master/cumulusci.yml
            https://raw.githubusercontent.com/SalesforceFoundation/Relationships/master/cumulusci.yml
            https://raw.githubusercontent.com/SalesforceFoundation/Volunteers-for-Salesforce/master/cumulusci.yml
            https://raw.githubusercontent.com/SalesforceFoundation/Recurring_Donations/master/cumulusci.yml
        """

        def raise_exception(error):
            raise Exception(error)

        def test_urls(urls_string, on_error_callback):
            urls = (url.strip() for url in good_urls.split("\n"))
            results = [
                (url, cci_safe_load(url, on_error=on_error_callback))
                for url in urls
                if url
            ]
            for url, data in results:
                assert "flows" in data, url

        # these ones should not trigger the error handler
        test_urls(good_urls, raise_exception)
        # these ones might, but they should still parse smoothly
        test_urls(bad_urls, lambda x: x)

    @pytest.mark.skipif(
        not os.environ.get("CCI_LOCAL_DIRECTORY_TESTS"),
        reason="CCI_LOCAL_DIRECTORY_TESTS environment variable not set",
    )  # you can turn this on if you happen to have this local file structure
    def test_from_local(self):
        assert parse_from_yaml("../Abacus/cumulusci.yml")
        assert parse_from_yaml("../NPSP/cumulusci.yml")
        assert parse_from_yaml("../CaseMan/cumulusci.yml")

    def test_steps_flow_and_task_heterogenous(self, caplog):
        yaml = """flows:
                    my_flow:
                        steps:
                            1:
                                flow: a
                            2:
                                task: b
                            """
        cci_data = cci_safe_load(StringIO(yaml))
        assert not caplog.text
        assert cci_data["flows"]["my_flow"]["steps"][1]["flow"] == "a"
        assert cci_data["flows"]["my_flow"]["steps"][2]["task"] == "b"

    def test_steps_as_list(self, caplog):
        yaml = """flows:
                    my_flow:
                        steps:
                            - A
                            - B
                            - C """
        assert not caplog.text
        cci_safe_load(StringIO(yaml))
        assert "my_flow" in caplog.text
        assert "steps" in caplog.text
        assert "dict" in caplog.text

    def test_individual_steps_as_list(self, caplog):
        yaml = """flows:
                    my_flow:
                        steps:
                            1:
                                - task : b
"""
        assert not caplog.text
        cci_safe_load(StringIO(yaml))
        print(caplog.text)
        assert "steps" in caplog.text
        assert "my_flow" in caplog.text
        assert "dict" in caplog.text

    def test_flow_and_task_confusion(self, caplog):
        yaml = """flows:
                    my_flow:
                        steps:
                            1:
                                task: b
                                flow: c
"""
        assert not caplog.text
        cci_safe_load(StringIO(yaml))
        assert "steps" in caplog.text
        assert "my_flow" in caplog.text

    def test_validate_files__no_errors(self, caplog):
        import cumulusci

        codedir = Path(cumulusci.__file__).parent.parent
        errs = _validate_files([str(codedir / "cumulusci.yml")])
        assert not errs

    def test_validate_files__with_errors(self, caplog):
        codedir = Path(__file__).parent
        errs = _validate_files([str(Path(codedir / "bad_cci.yml"))])
        assert errs

    @pytest.mark.vcr()
    def test_validate_url__with_errors(self, caplog):
        url = "https://raw.githubusercontent.com/SFDO-Tooling/CumulusCI/8b8d1eb9a1593503bf625030fa702b6d4651cb55/cumulusci/tasks/bulkdata/tests/snowfakery/simple_snowfakery.load.yml"
        errs = _validate_url(url)
        assert "sf_object" in str(errs)
        assert "extra fields not permitted" in str(errs)
        assert "snowfakery.load.yml" in str(errs)

    def test_validate_empty(self, caplog):
        out = cci_safe_load(StringIO(""))
        assert not caplog.text, caplog.text
        assert out == {}

    def test_custom(self, caplog):
        yaml = """project:
                    custom:
                        foo: X
                        bar:
                            - a
                            - b
                            - c
                        baz:
                            a: aa
                            b: bb
                            c: cc
"""
        cciyml = cci_safe_load(StringIO(yaml))
        assert not caplog.text
        assert cciyml["project"]["custom"]["foo"] == "X"
        assert cciyml["project"]["custom"]["bar"] == ["a", "b", "c"]
        assert cciyml["project"]["custom"]["baz"] == {
            "a": "aa",
            "b": "bb",
            "c": "cc",
        }


@pytest.fixture
def cci_yml_file():
    "Yields a cumulusci file obj for writing to. Cleans up when finished."
    with temporary_dir() as temp_dir:
        cumulusci_yml_filepath = Path(temp_dir) / "cumulusci.yml"

        with open(cumulusci_yml_filepath, "w+") as cumulusci_yml:
            yield cumulusci_yml


def test_mutually_exclusive_options():
    logger = MagicMock()
    with pytest.raises(AssertionError):
        cci_safe_load(StringIO(""), on_error=lambda *args: args, logger=logger)


def test_github_source():
    with pytest.raises(ValidationError):
        GitHubSourceModel(
            github="https://github.com/Test/TestRepo", commit="abcdef", release="foo"
        )

    GitHubSourceModel(github="https://github.com/Test/TestRepo", release="latest")

    assert (
        GitHubSourceModel(github="https://github.com/Test/TestRepo").resolution_strategy
        == "production"
    )


def test_single_primary_plan(caplog):
    yaml = """
plans:
  first:
    tier: primary
  second:
    tier: primary
    """
    cci_safe_load(StringIO(yaml))
    assert "Only one plan can be defined as 'primary' or 'secondary'" in caplog.text


def test_single_primary_plan_implicit(caplog):
    yaml = """
plans:
  explicit:
    tier: primary
  implicit:
    slug: implicit_primary
    """
    cci_safe_load(StringIO(yaml))
    assert "Only one plan can be defined as 'primary' or 'secondary'" in caplog.text


def test_single_secondary_plan(caplog):
    yaml = """
plans:
  first:
    tier: secondary
  second:
    tier: secondary
    """
    cci_safe_load(StringIO(yaml))
    assert "Only one plan can be defined as 'primary' or 'secondary'" in caplog.text


def test_multiple_additional_plan(caplog):
    yaml = """
plans:
  first:
    slug: implicit_primary
  second:
    tier: secondary
  third:
    tier: additional
  fourth:
    tier: additional
    """
    parsed_yaml: dict = cci_safe_load(StringIO(yaml))
    expected: dict = {
        "first": {"slug": "implicit_primary"},
        "second": {"tier": "secondary"},
        "third": {"tier": "additional"},
        "fourth": {"tier": "additional"},
    }
    assert "" == caplog.text
    assert expected == parsed_yaml["plans"]
