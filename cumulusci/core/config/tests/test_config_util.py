import json
import os
import pathlib
from unittest import mock

import pytest
import yaml

from cumulusci.core.config import ServiceConfig, SfdxOrgConfig, UniversalConfig
from cumulusci.core.config.project_config import BaseProjectConfig
from cumulusci.core.config.util import get_devhub_config
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.utils import temporary_dir, touch


@pytest.fixture
def repo_root():
    with temporary_dir() as path:
        os.mkdir(".git")
        os.mkdir("src")
        pathlib.Path(path, "src", "package.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n<Package xmlns="http://soap.sforce.com/2006/04/metadata"></Package>'
        )
        with open("cumulusci.yml", "w") as f:
            yaml.dump(
                {
                    "project": {
                        "dependencies": [
                            {
                                "name": "EDA unpackaged/pre/first",
                                "repo_owner": "SalesforceFoundation",
                                "repo_name": "EDA",
                                "subfolder": "unpackaged/pre/first",
                            },
                            {
                                "namespace": "hed",
                                "version": "1.99",
                                "dependencies": [
                                    {"namespace": "pub", "version": "1.5"}
                                ],
                            },
                        ]
                    }
                },
                f,
            )
        pathlib.Path(path, "unpackaged", "pre", "first").mkdir(parents=True)
        touch(os.path.join("unpackaged", "pre", "first", "package.xml"))
        yield path


@pytest.fixture
def project_config(repo_root):
    project_config = BaseProjectConfig(
        UniversalConfig(),
        repo_info={"root": repo_root, "branch": "main"},
    )
    project_config.config["project"]["package"]["install_class"] = "Install"
    project_config.config["project"]["package"]["uninstall_class"] = "Uninstall"
    project_config.keychain = BaseProjectKeychain(project_config, key=None)
    pathlib.Path(repo_root, "orgs").mkdir()
    pathlib.Path(repo_root, "orgs", "scratch_def.json").write_text(
        json.dumps(
            {
                "edition": "Developer",
                "settings": {},
            }
        )
    )

    project_config.get_github_api = mock.Mock()

    return project_config


def test_get_devhub_config__from_sfdx(project_config):
    with mock.patch(
        "cumulusci.core.config.util.get_default_devhub_username",
        return_value="devhub@example.com",
    ):
        result = get_devhub_config(project_config)
    assert isinstance(result, SfdxOrgConfig)
    assert result.username == "devhub@example.com"


def test_get_devhub_config__from_service(project_config, org_config):
    project_config.keychain.set_service(
        "devhub", "test_alias", ServiceConfig({"username": "devhub@example.com"})
    )
    devhub_config = get_devhub_config(project_config)
    assert devhub_config.username == "devhub@example.com"
