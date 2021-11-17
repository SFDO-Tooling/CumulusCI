from pathlib import Path
from unittest import mock
from unittest.mock import ANY

import pytest
from sarge import Capture

from cumulusci.core.config import TaskConfig
from cumulusci.core.config.project_config import BaseProjectConfig
from cumulusci.core.config.universal_config import UniversalConfig
from cumulusci.tasks.dx_convert_from import DxConvertFrom
from cumulusci.utils import temporary_dir


@pytest.fixture
def project_config():
    universal_config = UniversalConfig()
    project_config = BaseProjectConfig(universal_config, config={"no_yaml": True})
    project_config.project__name = "TestProject"
    return project_config


@pytest.fixture
def task_config():
    return TaskConfig({"options": {"command": "force:source:convert"}})


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
def test_dx_convert_from__src_exists(sarge, sarge_process, dx_convert_task):
    with temporary_dir():
        dir_structure = Path("src/inner_dir")
        dir_structure.mkdir(exist_ok=True, parents=True)

        src_file1_path = Path("src/foo.txt")
        src_file1_path.touch()

        src_file2_path = Path("src/inner_dir/foo.txt")
        src_file2_path.touch()

        sarge.Command.return_value = sarge_process
        dx_convert_task()

        assert Path("src").is_dir()
        assert not dir_structure.exists()
        assert not src_file1_path.exists()
        assert not src_file2_path.exists()
        sarge.Command.assert_called_once_with(
            "sfdx force:source:convert -d src",
            cwd=".",
            env=ANY,
            shell=True,
            stdout=ANY,
            stderr=ANY,
        )
