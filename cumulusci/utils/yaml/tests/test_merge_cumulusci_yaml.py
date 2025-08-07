from pathlib import Path

import pytest

from cumulusci.core.config.project_config import BaseProjectConfig
from cumulusci.core.config.universal_config import UniversalConfig
from cumulusci.core.exceptions import ConfigError
from cumulusci.utils import temporary_dir


def create_project_config(yaml) -> BaseProjectConfig:
    universal_config = UniversalConfig()

    with temporary_dir() as tmpdir:
        tmpdir = Path(tmpdir).resolve()

        cumulusci_yml_path = tmpdir / "cumulusci.yml"
        with open(cumulusci_yml_path, "w") as cumulusci_yml:
            cumulusci_yml.write(yaml)
        project_config = BaseProjectConfig(
            universal_config,
            {},
            repo_info={"root": tmpdir},
        )
        return project_config


class TestMergeCumulusCIYaml:
    def test_simple_extends_tasks(self):
        project_config = create_project_config(
            """
                    tasks:
                        whatever:
                            extends: log
                    """
        )
        task = project_config.get_task("whatever")
        assert task.class_path == "cumulusci.tasks.util.LogLine"

    def test_extends_tasks__no_parent_task_error(self):
        with pytest.raises(ConfigError, match="snowflokkery.*snowfakery"):
            create_project_config(
                """
                        tasks:
                            whatever:
                                extends: snowflokkery
                        """
            )

    def test_extends_tasks__extend_and_classpath_error(self, caplog):
        create_project_config(
            """
                        tasks:
                            whatever:
                                class_path: a.b.c.d
                                extends: log
                        """
        )
        assert "whatever" in caplog.text

    def test_extends_tasks__extend_and_override_error(self):
        with pytest.raises(ConfigError, match="itself"):
            create_project_config(
                """
                        tasks:
                            log:
                                extends: log
                        """
            )

    def test_extends_tasks__extend_and_override_itself_error(self):
        with pytest.raises(ConfigError, match="foo.*no previous"):
            create_project_config(
                """
                            tasks:
                                foo:
                                    extends: foo
                            """
            )

    def test_extends_tasks__extend_and_override_an_absstract_base(self):
        with pytest.raises(ConfigError, match="class_path.*bar"):
            create_project_config(
                """
                            tasks:
                                bar:
                                    options:
                                        xyzzy: Nothing happens

                                foo:
                                    extends: bar

                            """
            )

    def test_extends_tasks__extend_circular_reference__error(self):
        with pytest.raises(ConfigError, match="Circular.*foo"):
            create_project_config(
                """
                            tasks:
                                foo:
                                    extends: bar

                                bar:
                                    extends: baz
                                    options: {}

                                baz:
                                    extends: foo
                                    options: {}

                            """
            )
