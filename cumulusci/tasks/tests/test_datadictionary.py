import unittest

from cumulusci.tasks.datadictionary import GenerateDataDictionary
from cumulusci.tasks.salesforce.util import create_task
from cumulusci.tests.util import create_project_config
from distutils.version import LooseVersion
from unittest.mock import Mock


class test_GenerateDataDictionary(unittest.TestCase):
    def test_set_version_with_props(self):
        task = create_task(GenerateDataDictionary)

        this_dict = {"version": LooseVersion("1.1")}
        task._set_version_with_props(this_dict, {"version": None})

        assert this_dict["version"] == LooseVersion("1.1")

        this_dict = {"version": LooseVersion("1.1")}
        task._set_version_with_props(this_dict, {"version": "1.2"})

        assert this_dict["version"] == LooseVersion("1.2")

        this_dict = {"version": LooseVersion("1.3")}
        task._set_version_with_props(this_dict, {"version": "1.2"})

        assert this_dict["version"] == LooseVersion("1.3")

    def test_version_from_tag_name(self):
        task = create_task(GenerateDataDictionary)
        project_config = create_project_config("TestRepo", "TestOwner")
        project_config.project__package__git__prefix_release = "release/"

        assert task._version_from_tag_name("release/1.1") == LooseVersion("1.1")
