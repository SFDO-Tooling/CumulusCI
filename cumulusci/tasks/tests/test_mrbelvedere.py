import json
import mock
import unittest

import responses

from cumulusci.core.config import BaseGlobalConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.config import ServiceConfig
from cumulusci.core.config import TaskConfig
from cumulusci.core.exceptions import MrbelvedereError
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.tasks.mrbelvedere import MrbelvederePublish
from cumulusci.tests.util import get_base_config


class TestMrbelvederePublish(unittest.TestCase):
    def setUp(self):
        self.project_config = BaseProjectConfig(BaseGlobalConfig(), get_base_config())
        self.project_config.config["project"]["package"]["namespace"] = "npsp"
        self.project_config.config["project"]["dependencies"] = [
            {"namespace": "nochangedep", "version": "1.0"},
            {"namespace": "changedep", "version": "1.1"},
        ]
        keychain = BaseProjectKeychain(self.project_config, "")
        keychain.set_service(
            "mrbelvedere",
            ServiceConfig({"base_url": "http://mrbelvedere", "api_key": "1234"}),
        )
        self.project_config.set_keychain(keychain)
        self.task_config = TaskConfig({"options": {"tag": "beta/1.0-Beta_2"}})

    @responses.activate
    def test_run_task(self):
        responses.add(
            responses.GET,
            "http://mrbelvedere/npsp/dependencies/beta",
            body=json.dumps(
                [
                    {"namespace": "npsp", "number": "1.0 (Beta 1)"},
                    {"namespace": "changedep", "number": "1.0"},
                    {"namespace": "nochangedep", "number": "1.0"},
                    {"namespace": "other", "number": "1.0"},
                ]
            ),
        )
        responses.add(
            responses.POST, "http://mrbelvedere/npsp/dependencies/beta", status=200
        )

        task = MrbelvederePublish(self.project_config, self.task_config)
        task()

        result = json.loads(responses.calls[-1].request.body)
        self.assertEqual(
            [
                {"namespace": "changedep", "number": "1.1"},
                {"namespace": "npsp", "number": "1.0 (Beta 2)"},
            ],
            result,
        )

    @responses.activate
    def test_run_task__http_error(self):
        responses.add(
            responses.POST, "http://mrbelvedere/npsp/dependencies/beta", status=500
        )

        task = MrbelvederePublish(self.project_config, self.task_config)
        task._get_current_dependencies = mock.Mock(
            return_value=[{"namespace": "npsp", "number": "1.0 (Beta 1)"}]
        )
        with self.assertRaises(MrbelvedereError):
            task()

    def test_clean_dependencies(self):
        task = MrbelvederePublish(self.project_config, self.task_config)
        result = task._clean_dependencies(
            [
                {"github": "https://github.com/SFDO-Tooling/CumulusCI-Test"},
                {"namespace": "foo", "version": "1.0"},
                {"namespace": "foo", "version": "2.0", "dependencies": []},
            ]
        )
        self.assertEqual([{"namespace": "foo", "number": "2.0"}], result)

    def test_clean_dependencies__no_deps(self):
        task = MrbelvederePublish(self.project_config, self.task_config)
        result = task._clean_dependencies([])
        self.assertEqual([], result)
