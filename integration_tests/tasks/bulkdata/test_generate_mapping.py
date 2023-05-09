from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.bulkdata import GenerateMapping


class TestGenerateMapping:
    def test_simple_generate(self, create_task):
        with TemporaryDirectory() as t:
            tempfile = Path(t) / "tempfile.mapping.yml"

            task = create_task(GenerateMapping, {"path": tempfile})
            assert not Path(tempfile).exists()
            task()
            assert Path(tempfile).exists()

    def test_error(self, create_task):
        with TemporaryDirectory() as t:
            tempfile = Path(t) / "tempfile.mapping.yml"
            task = create_task(GenerateMapping, {"path": tempfile, "include": "Foo"})
            with pytest.raises(TaskOptionsError) as e:
                task()
            assert "Foo" in str(e.value)
