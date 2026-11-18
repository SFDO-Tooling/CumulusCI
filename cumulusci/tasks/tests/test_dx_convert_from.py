import json
from pathlib import Path
from unittest import mock
from unittest.mock import ANY

import pytest
from sarge import Capture

from cumulusci.core.config import TaskConfig
from cumulusci.core.config.project_config import BaseProjectConfig
from cumulusci.core.config.universal_config import UniversalConfig
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.dx_convert_from import DxConvertFrom
from cumulusci.tasks.sfdx import DxConvertTo
from cumulusci.utils import temporary_dir


@pytest.fixture
def project_config():
    universal_config = UniversalConfig()
    project_config = BaseProjectConfig(universal_config, config={"no_yaml": True})
    project_config.project__name = "TestProject"
    return project_config


@pytest.fixture
def task_config():
    return TaskConfig({"options": {"src_dir": "src"}})


@pytest.fixture
def sarge_process():
    p = mock.Mock()
    p.returncode = 0
    p.stdout = Capture()
    p.stderr = Capture()
    return p


@pytest.fixture
def dx_convert_task(project_config, task_config):
    return DxConvertFrom(project_config, task_config)


@mock.patch("cumulusci.tasks.command.sarge")
def test_dx_convert_from(sarge, sarge_process, dx_convert_task):
    """Ensure that we clear out the `src/`"""
    with temporary_dir():
        src_dir = Path("src")
        src_dir.mkdir(exist_ok=True)

        sarge.Command.return_value = sarge_process
        dx_convert_task()

        assert not src_dir.exists()
        sarge.Command.assert_called_once_with(
            "sf project convert source -d src",
            cwd=".",
            env=ANY,
            shell=True,
            stdout=ANY,
            stderr=ANY,
        )


def test_dx_convert_from_preserves_source_when_output_overlaps(
    project_config, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    project_config.repo_info["root"] = str(tmp_path)
    source = tmp_path / "metadata" / "my-app"
    source.mkdir(parents=True)
    (source / "keep-me.txt").touch()
    (tmp_path / "sfdx-project.json").write_text(
        json.dumps(
            {"packageDirectories": [{"path": "metadata/my-app", "default": True}]}
        ),
        encoding="utf-8",
    )
    task = DxConvertFrom(
        project_config, TaskConfig({"options": {"src_dir": "metadata"}})
    )

    with pytest.raises(TaskOptionsError, match="overlaps Salesforce DX source"):
        task()

    assert (source / "keep-me.txt").is_file()


@mock.patch("platform.system", return_value="Windows")
def test_dx_convert_to_uses_custom_mdapi_directory(platform_system, project_config):
    project_config.config["project"] = {"package": {"directory": "metadata/my app"}}
    task = DxConvertTo(project_config, TaskConfig({}))
    assert task._get_command() == 'sf project convert mdapi -r "metadata/my app"'

    override = DxConvertTo(project_config, TaskConfig({}), command="custom command")
    assert override._get_command() == "sf custom command"
