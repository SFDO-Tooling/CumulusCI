# -*- coding: utf-8 -*-

import io
import os
import zipfile
from datetime import datetime
from unittest import mock
from xml.etree import ElementTree as ET

import pytest
import responses
import sarge

from cumulusci import utils
from cumulusci.core.config import FlowConfig, TaskConfig
from cumulusci.core.exceptions import CumulusCIException
from cumulusci.core.flowrunner import FlowCoordinator
from cumulusci.core.tasks import BaseTask
from cumulusci.tests.util import create_project_config
from cumulusci.utils.xml import elementtree_parse_file, lxml_parse_file


class FunTestTask(BaseTask):
    """For testing doc_task"""

    task_options = {
        "color": {"description": "What color"},
        "size": {"description": "How big"},
        "flavor": {
            "description": "What flavor",
            "required": True,
            "usage": "--flavor VANILLA",
            "type": "string",
            "default": "chocolate",
        },
    }
    task_docs = "extra docs"


class FunTestTaskChild(FunTestTask):
    """For testing doc_task"""

    task_options = {
        "flavor": {"description": "What flavor", "required": True},
        "color": {"description": "What color"},
    }


@pytest.fixture
def task_config():
    return TaskConfig(
        {
            "class_path": "cumulusci.tests.test_utils.FunTestTask",
            "description": "Scoops icecream",
            "options": {"color": "black"},
        }
    )


@pytest.fixture
def option_info():
    return [
        {
            "name": "option_one",
            "required": True,
            "default": "default",
            "description": "description",
            "option_type": "option_type",
        },
        {
            "name": "option_two",
            "required": False,
            "description": "Brief description here.",
        },
    ]


class TestUtils:
    def test_find_replace(self):
        with utils.temporary_dir() as d:
            path = os.path.join(d, "test")
            with open(path, "w") as f:
                f.write("foo")

            logger = mock.Mock()
            utils.find_replace("foo", "bar", d, "*", logger)

            logger.info.assert_called_once()
            with open(path, "r") as f:
                result = f.read()
            assert result == "bar"

    def test_find_replace_max(self):
        with utils.temporary_dir() as d:
            path = os.path.join(d, "test")
            with open(path, "w") as f:
                f.write("aa")

            logger = mock.Mock()
            utils.find_replace("a", "b", d, "*", logger, max=1)

            logger.info.assert_called_once()
            with open(path, "r") as f:
                result = f.read()
            assert result == "ba"

    def test_find_replace_regex(self):
        with utils.temporary_dir() as d:
            path = os.path.join(d, "test")
            with open(path, "w") as f:
                f.write("aa")

            logger = mock.Mock()
            utils.find_replace_regex(r"\w", "x", d, "*", logger)

            logger.info.assert_called_once()
            with open(path, "r") as f:
                result = f.read()
            assert result == "xx"

    def test_find_rename(self):
        with utils.temporary_dir() as d:
            path = os.path.join(d, "foo")
            with open(path, "w") as f:
                f.write("aa")

            logger = mock.Mock()
            utils.find_rename("foo", "bar", d, logger)

            logger.info.assert_called_once()
            assert os.listdir(d) == ["bar"]

    def test_elementtree_parse_file(self, cumulusci_test_repo_root):
        tree = elementtree_parse_file(
            cumulusci_test_repo_root / "cumulusci/files/admin_profile.xml"
        )
        assert tree.getroot().tag.startswith("{")

    def test_elementtree_parse_file_pathstr(self, cumulusci_test_repo_root):
        tree = elementtree_parse_file(
            str(cumulusci_test_repo_root / "cumulusci/files/admin_profile.xml")
        )
        assert tree.getroot().tag.startswith("{")

    def test_lxml_parse_file(self, cumulusci_test_repo_root):
        tree = lxml_parse_file(
            cumulusci_test_repo_root / "cumulusci/files/admin_profile.xml"
        )
        assert tree.getroot().tag.startswith("{")

    def test_lxml_parse_stream(self, cumulusci_test_repo_root):
        data = io.StringIO("<Foo/>")
        tree = lxml_parse_file(data)
        assert tree.getroot().tag == "Foo"

    def test_lxml_parse_file_pathstr(self, cumulusci_test_repo_root):
        tree = lxml_parse_file(
            str(cumulusci_test_repo_root / "cumulusci/files/admin_profile.xml")
        )
        assert tree.getroot().tag.startswith("{")

    def test_elementtree_parse_stream(self, cumulusci_test_repo_root):
        data = io.StringIO("<Foo/>")
        tree = elementtree_parse_file(data)
        assert tree.getroot().tag == "Foo"

    @mock.patch("xml.etree.ElementTree.parse")
    def test_elementtree_parse_file_error(self, mock_parse):
        err = ET.ParseError()
        err.msg = "it broke"
        err.lineno = 1
        mock_parse.side_effect = err
        try:
            utils.elementtree_parse_file("test_file")
        except ET.ParseError as err:
            assert str(err) == "it broke (test_file, line 1)"
        else:
            assert False  # Expected ParseError

    def test_remove_xml_element_directory(self):
        with utils.temporary_dir() as d:
            path = os.path.join(d, "test.xml")
            with open(path, "w") as f:
                f.write(
                    '<?xml version="1.0" ?>'
                    '<root xmlns="http://soap.sforce.com/2006/04/metadata">'
                    "<tag>text</tag></root>"
                )

            utils.remove_xml_element_directory("tag", d, "*")

            with open(path, "r") as f:
                result = f.read()
            expected = """<?xml version='1.0' encoding='UTF-8'?>
<root xmlns="http://soap.sforce.com/2006/04/metadata" />"""
            assert expected == result

    @mock.patch("xml.etree.ElementTree.parse")
    def test_remove_xml_element_parse_error(self, mock_parse):
        err = ET.ParseError()
        err.msg = "it broke"
        err.lineno = 1
        mock_parse.side_effect = err
        with utils.temporary_dir() as d:
            path = os.path.join(d, "test.xml")
            with open(path, "w") as f:
                f.write(
                    '<?xml version="1.0" ?>'
                    '<root xmlns="http://soap.sforce.com/2006/04/metadata">'
                    "<tag>text</tag></root>"
                )
            try:
                utils.remove_xml_element_directory("tag", d, "*")
            except ET.ParseError as err:
                assert str(err) == "it broke (test.xml, line 1)"
            else:
                assert False  # Expected ParseError

    def test_remove_xml_element_not_found(self):
        tree = ET.fromstring("<root />")
        result = utils.remove_xml_element("tag", tree)
        assert result is tree

    def test_doc_task(self, task_config):
        task_doc = utils.doc_task("scoop_icecream", task_config)
        assert (
            task_doc
            == """.. _scoop-icecream:

scoop_icecream
==========================================\n
**Description:** Scoops icecream\n
**Class:** cumulusci.tests.test_utils.FunTestTask\n
extra docs
Command Syntax\n------------------------------------------\n
``$ cci task run scoop_icecream``\n\n
Options\n------------------------------------------\n\n
``--flavor VANILLA``

\t What flavor
\n *Required*\n
\t Type: string\n
``--color COLOR``\n
\t What color\n
\t Default: black\n
``--size SIZE``
\n\t How big
\n *Optional*"""
        )

    def test_get_command_syntax(self, task_config):
        task_name = "scoop_icecream"
        cmd_syntax = utils.get_command_syntax(task_name)

        assert cmd_syntax == "``$ cci task run scoop_icecream``\n\n"

    def test_get_task_options_info(self, task_config):
        option_info = utils.get_task_option_info(task_config, FunTestTask)

        # Required options should be at the front of the list
        assert option_info[0]["required"]
        assert option_info[0]["description"] == "What flavor"
        assert option_info[0]["usage"] == "--flavor VANILLA"
        assert option_info[0]["name"] == "flavor"
        assert option_info[0]["option_type"] == "string"
        assert option_info[0]["default"] is None

        assert not option_info[1]["required"]
        assert option_info[1]["default"] == "black"
        assert option_info[1]["usage"] == "--color COLOR"

        assert not option_info[2]["required"]
        assert option_info[2]["default"] is None
        assert option_info[2]["usage"] == "--size SIZE"

    def test_get_option_usage_string(self, option_info):
        name = option_info[0]["name"]
        usage_str1 = utils.get_option_usage_string(name, option_info[0])
        assert usage_str1 == "--option_one OPTIONONE"

        name = option_info[1]["name"]
        usage_str2 = utils.get_option_usage_string(name, option_info[1])
        assert usage_str2 == "--option_two OPTIONTWO"

    def test_create_task_options_doc(self, option_info):
        option_one_doc = utils.create_task_options_doc(option_info[:1])
        option_two_doc = utils.create_task_options_doc(option_info[1:])
        assert option_one_doc == [
            "\n\t description",
            "\n\t Default: default",
            "\n\t Type: option_type",
        ]

        assert option_two_doc == ["\n\t Brief description here.", "\n *Optional*"]

    def test_document_flow(self):
        project_config = create_project_config("TestOwner", "TestRepo")
        flow_config = FlowConfig({"description": "Test Flow", "steps": {}})
        coordinator = FlowCoordinator(project_config, flow_config, name="test_flow")
        flow_doc = utils.document_flow("test flow", "test description.", coordinator)

        expected_doc = (
            ".. _test flow:\n\n"
            "test flow"
            "\n^^^^^^^^^\n"
            "\n**Description:** test description.\n"
            "\n**Flow Steps**\n"
            "\n.. code-block:: console\n"
        )

        assert expected_doc == flow_doc, flow_doc

    def test_document_flow__additional_info(self):
        flow_steps = ["1) (Task) Extract"]
        flow_coordinator = mock.Mock(get_flow_steps=mock.Mock(return_value=flow_steps))
        other_info = "**this is** just some rst ``formatted`` text."

        flow_doc = utils.document_flow(
            "test flow",
            "test description.",
            flow_coordinator,
            additional_info=other_info,
        )

        expected_doc = (
            ".. _test flow:\n\n"
            "test flow"
            "\n^^^^^^^^^\n"
            "\n**Description:** test description.\n"
            f"\n{other_info}"
            "\n**Flow Steps**\n"
            "\n.. code-block:: console\n"
            "\n\t1) (Task) Extract"
        )
        if expected_doc != flow_doc:
            print(repr(expected_doc))
            print(repr(flow_doc))
        assert expected_doc == flow_doc

    @responses.activate
    def test_download_extract_zip(self):
        f = io.BytesIO()
        with zipfile.ZipFile(f, "w") as zf:
            zf.writestr("top", "top")
            zf.writestr("folder/test", "test")
        f.seek(0)
        zipbytes = f.read()
        responses.add(
            method=responses.GET,
            url="http://test",
            body=zipbytes,
            content_type="application/zip",
        )

        zf = utils.download_extract_zip("http://test", subfolder="folder")
        result = zf.read("test")
        assert b"test" == result

    @responses.activate
    def test_download_extract_zip_to_target(self):
        with utils.temporary_dir() as d:
            f = io.BytesIO()
            with zipfile.ZipFile(f, "w") as zf:
                zf.writestr("test", "test")
            f.seek(0)
            zipbytes = f.read()
            responses.add(
                method=responses.GET,
                url="http://test",
                body=zipbytes,
                content_type="application/zip",
            )

            utils.download_extract_zip("http://test", target=d)
            assert "test" in os.listdir(d)

    def test_download_extract_github(self):
        f = io.BytesIO()
        with zipfile.ZipFile(f, "w") as zf:
            zf.writestr("top/", "top")
            zf.writestr("top/src/", "top_src")
            zf.writestr("top/src/test", "test")
        f.seek(0)
        zipbytes = f.read()
        mock_repo = mock.Mock(default_branch="main")
        mock_github = mock.Mock()
        mock_github.repository.return_value = mock_repo

        def assign_bytes(archive_type, zip_content, ref=None):
            zip_content.write(zipbytes)
            return True

        mock_archive = mock.Mock(side_effect=assign_bytes)
        mock_repo.archive = mock_archive
        zf = utils.download_extract_github(mock_github, "TestOwner", "TestRepo", "src")
        result = zf.read("test")
        assert b"test" in result

    def test_download_extract_github__failure(self):
        mock_repo = mock.Mock(default_branch="main")
        mock_github = mock.Mock()
        mock_github.repository.return_value = mock_repo

        mock_repo.archive.return_value = False
        with pytest.raises(CumulusCIException) as e:
            utils.download_extract_github(mock_github, "TestOwner", "TestRepo", "src")
            assert "Unable to download a zipball" in str(e)

    def test_process_text_in_directory__renamed_file(self):
        with utils.temporary_dir():
            with open("test1", "w") as f:
                f.write("test")

            def process(name, content):
                return "test2", "test"

            utils.process_text_in_directory(".", process)

            with open("test2", "r") as f:
                result = f.read()
            assert result == "test"

    def test_process_text_in_directory__skips_binary(self):
        contents = b"\x9c%%%NAMESPACE%%%"
        with utils.temporary_dir():
            with open("test", "wb") as f:
                f.write(contents)

            def process(name, content):
                return name, ""

            utils.process_text_in_directory(".", process)

            # assert contents were untouched
            with open("test", "rb") as f:
                result = f.read()
            assert contents == result

    def test_process_text_in_zipfile__skips_binary(self):
        contents = b"\x9c%%%NAMESPACE%%%"
        zf = zipfile.ZipFile(io.BytesIO(), "w")
        zf.writestr("test", contents)

        def process(name, content):
            return name, ""

        zf = utils.process_text_in_zipfile(zf, process)
        result = zf.read("test")
        # assert contents were untouched
        assert contents == result
        zf.close()

    def test_inject_namespace__managed(self):
        logger = mock.Mock()
        name = "___NAMESPACE___test"
        content = "%%%NAMESPACE%%%|%%%NAMESPACE_DOT%%%|%%%NAMESPACED_ORG%%%|%%%NAMESPACE_OR_C%%%|%%%NAMESPACED_ORG_OR_C%%%"

        name, content = utils.inject_namespace(
            name, content, namespace="ns", managed=True, logger=logger
        )
        assert name == "ns__test"
        assert content == "ns__|ns.||ns|c"

    def test_inject_namespace__unmanaged(self):
        name = "___NAMESPACE___test"
        content = "%%%NAMESPACE%%%|%%%NAMESPACE_DOT%%%|%%%NAMESPACED_ORG%%%|%%%NAMESPACE_OR_C%%%|%%%NAMESPACED_ORG_OR_C%%%"

        name, content = utils.inject_namespace(name, content, namespace="ns")
        assert name == "test"
        assert content == "|||c|c"

    def test_inject_namespace__namespaced_org(self):
        name = "___NAMESPACE___test"
        content = "%%%NAMESPACE%%%|%%%NAMESPACE_DOT%%%|%%%NAMESPACED_ORG%%%|%%%NAMESPACE_OR_C%%%|%%%NAMESPACED_ORG_OR_C%%%"

        name, content = utils.inject_namespace(
            name, content, namespace="ns", managed=True, namespaced_org=True
        )
        assert name == "ns__test"
        assert content == "ns__|ns.|ns__|ns|ns"

    def test_inject_namespace__filename_token_in_package_xml(self):
        name, content = utils.inject_namespace(
            "package.xml", "___NAMESPACE___", namespace="ns", managed=True
        )
        assert content == "ns__"

    def test_strip_namespace(self):
        logger = mock.Mock()
        name, content = utils.strip_namespace(
            name="ns__test", content="ns__test ns:test", namespace="ns", logger=logger
        )
        assert name == "test"
        assert content == "test c:test"
        logger.info.assert_called_once()

    def test_tokenize_namespace(self):
        name, content = utils.tokenize_namespace(
            name="ns__test", content="ns__test ns:test", namespace="ns"
        )
        assert name == "___NAMESPACE___test"
        assert content == "%%%NAMESPACE%%%test %%%NAMESPACE_OR_C%%%test"

    def test_tokenize_namespace__no_namespace(self):
        name, content = utils.tokenize_namespace(name="test", content="", namespace="")
        assert name is name
        assert content is content

    def test_zip_clean_metaxml(self):
        logger = mock.Mock()
        zf = zipfile.ZipFile(io.BytesIO(), "w")
        zf.writestr(
            "classes/test-meta.xml",
            '<?xml version="1.0" ?>'
            '<root xmlns="http://soap.sforce.com/2006/04/metadata">'
            "<packageVersions>text</packageVersions></root>",
        )
        zf.writestr("test", "")
        zf.writestr("other/test-meta.xml", "")

        zf = utils.zip_clean_metaxml(zf, logger=logger)
        result = zf.read("classes/test-meta.xml")
        assert b"packageVersions" not in result
        assert "other/test-meta.xml" in zf.namelist()
        zf.close()

    def test_zip_clean_metaxml__skips_binary(self):
        logger = mock.Mock()
        zf = zipfile.ZipFile(io.BytesIO(), "w")
        zf.writestr("classes/test-meta.xml", b"\x9c")
        zf.writestr("test", "")
        zf.writestr("other/test-meta.xml", "")

        zf = utils.zip_clean_metaxml(zf, logger=logger)
        assert "classes/test-meta.xml" in zf.namelist()
        zf.close()

    def test_zip_clean_metaxml__handles_nonascii(self):
        zf = zipfile.ZipFile(io.BytesIO(), "w")
        zf.writestr("classes/test-meta.xml", b"<root>\xc3\xb1</root>")

        zf = utils.zip_clean_metaxml(zf)
        assert b"<root>\xc3\xb1</root>" == zf.read("classes/test-meta.xml")
        zf.close()

    def test_doc_task_not_inherited(self):
        task_config = TaskConfig(
            {
                "class_path": "cumulusci.tests.test_utils.FunTestTaskChild",
                "options": {"color": "black"},
            }
        )
        result = utils.doc_task("command", task_config)

        assert "extra docs" not in result

    def test_package_xml_from_dict(self):
        items = {"ApexClass": ["TestClass"]}
        result = utils.package_xml_from_dict(
            items, api_version="43.0", package_name="TestPackage"
        )
        assert (
            """<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>TestPackage</fullName>
    <types>
        <members>TestClass</members>
        <name>ApexClass</name>
    </types>
    <version>43.0</version>
</Package>"""
            == result
        )

    def test_cd__no_path(self):
        cwd = os.getcwd()
        with utils.cd(None):
            assert cwd == os.getcwd()

    def test_in_directory(self):
        cwd = os.getcwd()
        assert utils.in_directory(".", cwd)
        assert not utils.in_directory("..", cwd)

    def test_parse_api_datetime__good(self):
        good_str = "2018-08-07T16:00:56.000+0000"
        dt = utils.parse_api_datetime(good_str)
        assert dt == datetime(2018, 8, 7, 16, 0, 56)

    def test_parse_api_datetime__bad(self):
        bad_str = "2018-08-07T16:00:56.000-20000"
        with pytest.raises(AssertionError):
            utils.parse_api_datetime(bad_str)

    def test_log_progress(self):
        logger = mock.Mock()
        for x in utils.log_progress(range(3), logger, batch_size=1):
            pass
        assert 4 == logger.info.call_count

    def test_util__sets_homebrew_deprecation_msg(self):
        utils.CUMULUSCI_PATH = "/usr/local/Cellar/cumulusci/2.1.2"
        upgrade_cmd = utils.get_cci_upgrade_command()
        assert utils.BREW_DEPRECATION_MSG == upgrade_cmd

    def test_util__sets_linuxbrew_deprecation_msg(self):
        utils.CUMULUSCI_PATH = "/home/linuxbrew/.linuxbrew/cumulusci/2.1.2"
        upgrade_cmd = utils.get_cci_upgrade_command()
        assert utils.BREW_DEPRECATION_MSG == upgrade_cmd

    def test_util__sets_pip_upgrade_cmd(self):
        utils.CUMULUSCI_PATH = "/usr/local/pip-path/cumulusci/2.1.2"
        upgrade_cmd = utils.get_cci_upgrade_command()
        assert utils.PIP_UPDATE_CMD == upgrade_cmd

    def test_util__sets_pipx_upgrade_cmd(self):
        utils.CUMULUSCI_PATH = (
            "/Users/Username/.local/pipx/venvs/cumulusci/Lib/site-packages/cumulusci"
        )
        upgrade_cmd = utils.get_cci_upgrade_command()
        assert utils.PIPX_UPDATE_CMD == upgrade_cmd

    def test_convert_to_snake_case(self):
        assert utils.convert_to_snake_case("OneTwo") == "one_two"
        assert utils.convert_to_snake_case("ONETwo") == "one_two"
        assert utils.convert_to_snake_case("One_Two") == "one_two"

    @mock.patch("sarge.Command")
    def test_get_git_config(self, Command):
        Command.return_value = p = mock.Mock(
            stdout=io.BytesIO(b"test@example.com"), stderr=io.BytesIO(b""), returncode=0
        )

        assert utils.get_git_config("user.email") == "test@example.com"
        assert (
            sarge.shell_format('git config --get "{0!s}"', "user.email")
            == Command.call_args[0][0]
        )
        p.run.assert_called_once()

    @mock.patch("sarge.Command")
    def test_get_git_config_undefined(self, Command):
        Command.return_value = p = mock.Mock(
            stdout=io.BytesIO(b""), stderr=io.BytesIO(b""), returncode=0
        )

        assert utils.get_git_config("user.email") is None
        p.run.assert_called_once()

    @mock.patch("sarge.Command")
    def test_get_git_config_error(self, Command):
        Command.return_value = p = mock.Mock(
            stdout=io.BytesIO(b"Text"), stderr=io.BytesIO(b""), returncode=-1
        )

        assert utils.get_git_config("user.email") is None
        p.run.assert_called_once()
