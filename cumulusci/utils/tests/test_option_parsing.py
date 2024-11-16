from datetime import date
from pathlib import Path

import pytest

from cumulusci.core.config import (
    BaseProjectConfig,
    OrgConfig,
    TaskConfig,
    UniversalConfig,
)
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.tasks import BaseTask
from cumulusci.utils.options import (
    READONLYDICT_ERROR_MSG,
    CCIOptions,
    Field,
    ListOfStringsOption,
    MappingOption,
    ReadOnlyOptions,
)

ORG_ID = "00D000000000001"
USERNAME = "sample@example"


class TaskToTestTypes(BaseTask):
    class Options(CCIOptions):
        the_list: ListOfStringsOption = Field(
            default=[],
            description="A list of strings",
        )
        the_mapping: MappingOption = Field(
            default=[],
            description="A list of strings",
        )
        the_date: date = Field(default=None, description="A date")
        the_bool: bool = Field(default=True, description="A bool")
        the_path: Path = Field(default=None, description="A bool")
        req: int = Field(..., description="Mandatory int")

    parsed_options: Options

    def _run_task(self):
        for key, value in vars(self.parsed_options).items():
            if value:
                print(key, repr(getattr(self.parsed_options, key)))


class TaskWithoutOptions(BaseTask):
    pass


class TestTaskOptionsParsing:
    def setup_class(self):
        self.global_config = UniversalConfig()
        self.project_config = BaseProjectConfig(
            self.global_config, config={"noyaml": True}
        )
        self.org_config = OrgConfig({"username": USERNAME, "org_id": ORG_ID}, "test")
        self.task_config = TaskConfig(
            {
                "options": {
                    "the_list": ["a"],
                    "the_mapping": {"b": "c"},
                    "the_date": date(2019, 1, 30),
                    "the_bool": True,
                    "req": 1,
                }
            }
        )

    def test_noop(self):
        task = TaskToTestTypes(self.project_config, self.task_config, self.org_config)
        task._init_options({})
        assert task.options["the_list"] == ["a"]
        assert task.options["the_mapping"] == {"b": "c"}
        assert task.options["the_date"] == date(2019, 1, 30)
        assert task.options["the_bool"] is True
        assert task.parsed_options.the_list == task.options["the_list"]
        assert task.parsed_options.the_mapping == task.options["the_mapping"]
        assert task.parsed_options.the_date == task.options["the_date"]
        assert task.parsed_options.the_bool == task.options["the_bool"]

    def test_split_list(self):
        task_config = TaskConfig({"options": {"the_list": "a,b,c,d,e", "req": 1}})
        task = TaskToTestTypes(self.project_config, task_config, self.org_config)
        assert task.parsed_options.the_list == ["a", "b", "c", "d", "e"]

    def test_split_dict(self):
        task_config = TaskConfig(
            {"options": {"the_mapping": "a:aa,b:bb,c:cc", "req": 1}}
        )
        task = TaskToTestTypes(self.project_config, task_config, self.org_config)
        assert task.parsed_options.the_mapping == {"a": "aa", "b": "bb", "c": "cc"}

    def test_parse_date(self):
        task_config = TaskConfig({"options": {"the_date": "1972-11-03", "req": 1}})
        task = TaskToTestTypes(self.project_config, task_config, self.org_config)
        assert task.parsed_options.the_date == date(1972, 11, 3)

    def test_parse_bool(self):
        task_config = TaskConfig({"options": {"the_bool": "False", "req": 1}})
        task = TaskToTestTypes(self.project_config, task_config, self.org_config)
        assert task.parsed_options.the_bool is False

    def test_parse_path(self):
        task_config = TaskConfig({"options": {"the_path": __file__, "req": 1}})
        task = TaskToTestTypes(self.project_config, task_config, self.org_config)
        assert task.parsed_options.the_path.exists()

    def test_missing_option(self):
        task_config = TaskConfig({"options": {"the_path": __file__}})
        with pytest.raises(TaskOptionsError) as e:
            TaskToTestTypes(self.project_config, task_config, self.org_config)
        assert "req" in str(e.value)
        assert "required" in str(e.value)

    def test_wrong_option_type(self):
        task_config = TaskConfig({"options": {"the_bool": "Negatory", "req": 1}})
        with pytest.raises(TaskOptionsError) as e:
            TaskToTestTypes(self.project_config, task_config, self.org_config)
        assert "the_bool" in str(e.value)
        assert "boolean" in str(e.value)

    def test_extra_options(self):
        task_config = TaskConfig({"options": {"foo": "bar", "req": 1}})
        with pytest.raises(TaskOptionsError) as e:
            TaskToTestTypes(self.project_config, task_config, self.org_config)
        assert "foo" in str(e.value)
        assert "extra options" in str(e.value)

    def test_exception_in_parsing(self):
        task_config = TaskConfig(
            {"options": {"the_mapping": "aaaaa,bbbb:cccc", "req": 1}}
        )
        with pytest.raises(TaskOptionsError) as e:
            TaskToTestTypes(self.project_config, task_config, self.org_config)
        assert "the_mapping" in str(e.value)
        assert "name/value" in str(e.value)

    def test_wrong_type(self):
        task_config = TaskConfig({"options": {"the_path": 5, "req": 1}})
        with pytest.raises(TaskOptionsError) as e:
            TaskToTestTypes(self.project_config, task_config, self.org_config)
        assert "the_path" in str(e.value)
        assert "path" in str(e.value)

    def test_null_for_required(self):
        task_config = TaskConfig({"options": {"the_path": None, "req": None}})
        with pytest.raises(TaskOptionsError) as e:
            TaskToTestTypes(self.project_config, task_config, self.org_config)
        assert "req" in str(e.value)
        assert "none" in str(e.value)

    def test_multiple_errors(self):
        task_config = TaskConfig({"options": {"the_bool": "Nope"}})
        with pytest.raises(TaskOptionsError) as e:
            TaskToTestTypes(self.project_config, task_config, self.org_config)
        assert "the_bool" in str(e.value)
        assert "req" in str(e.value)
        assert "Errors" in str(e.value)

    def test_options_read_only(self):
        # Has an Options class
        task1 = TaskToTestTypes(self.project_config, self.task_config, self.org_config)
        assert isinstance(task1.options, ReadOnlyOptions)
        # Does not have an Options class
        task2 = TaskWithoutOptions(
            self.project_config, self.task_config, self.org_config
        )
        assert isinstance(task2.options, dict)

    def test_init_options__options_read_only_error(self):
        expected_error_msg = READONLYDICT_ERROR_MSG
        task = TaskToTestTypes(self.project_config, self.task_config, self.org_config)
        # Add new option
        with pytest.raises(TaskOptionsError, match=expected_error_msg):
            task.options["new_option"] = "something"
        # Modify existing option
        with pytest.raises(TaskOptionsError, match=expected_error_msg):
            task.options["test_option"] = 456
        # Delete existing option
        with pytest.raises(TaskOptionsError, match=expected_error_msg):
            del task.options["test_option"]
        # Pop existing option
        with pytest.raises(TaskOptionsError, match=expected_error_msg):
            task.options.pop("test_option")
