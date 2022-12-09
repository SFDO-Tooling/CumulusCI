import typing as T
from contextlib import contextmanager
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from shutil import rmtree
from tempfile import TemporaryDirectory

import yaml
from simple_salesforce import Salesforce

from cumulusci.core import exceptions as exc
from cumulusci.core.config import BaseProjectConfig, OrgConfig, TaskConfig
from cumulusci.salesforce_api.org_schema import Filters, Schema, get_org_schema
from cumulusci.tasks.bulkdata.extract import ExtractData
from cumulusci.tasks.bulkdata.extract_dataset_utils.extract_yml import (
    ExtractDeclaration,
    ExtractRulesFile,
)
from cumulusci.tasks.bulkdata.extract_dataset_utils.synthesize_extract_declarations import (
    SimplifiedExtractDeclaration,
    flatten_declarations,
)
from cumulusci.tasks.bulkdata.generate_mapping_utils.extract_mapping_file_generator import (
    create_extract_mapping_file_from_declarations,
)
from cumulusci.tasks.bulkdata.generate_mapping_utils.generate_mapping_from_declarations import (
    create_load_mapping_file_from_extract_declarations,
)
from cumulusci.tasks.bulkdata.load import LoadData
from cumulusci.tasks.bulkdata.snowfakery import Snowfakery


@dataclass
class Dataset:
    name: str
    project_config: BaseProjectConfig
    sf: Salesforce
    org_config: OrgConfig
    schema: Schema = None
    initialized = False

    @property
    def path(self) -> Path:
        return Path(self.project_config.repo_root) / "datasets" / self.name

    @property
    def extract_file(self) -> Path:
        return self.path / f"{self.name}.extract.yml"

    @property
    def mapping_file(self) -> Path:
        return self.path / f"{self.name}.mapping.yml"

    @property
    def data_file(self) -> Path:
        return self.path / f"{self.name}.dataset.sql"

    def exists(self) -> bool:
        return self.path.exists()

    def delete(self):
        rmtree(str(self.path))

    def __enter__(self, *args, **kwargs):
        if self.schema is None:
            self.schema_context = self._get_org_schema()
            self.schema = self.schema_context.__enter__(*args, **kwargs)
        else:
            self.schema_context = None
        self.initialized = True
        return self

    def __exit__(self, *args, **kwargs):
        if self.schema_context:
            self.schema_context.__exit__(*args, **kwargs)

    def create(self):
        assert (
            self.initialized
        ), "You must open this context manager. e.g. `with Dataset() as dataset`"

        if not self.path.exists():
            self.path.mkdir()

        self.extract_file.write_text(DEFAULT_EXTRACT_DATA)
        decls = ExtractRulesFile.parse_extract(StringIO(DEFAULT_EXTRACT_DATA))

        decls = list(decls.values())
        self._save_load_mapping(decls)

    def _get_org_schema(self):
        return get_org_schema(
            self.sf,
            self.org_config,
            include_counts=True,
            filters=[Filters.extractable, Filters.createable, Filters.populated],
        )

    def _save_load_mapping(self, decls: T.Sequence[ExtractDeclaration]) -> None:
        mapping_data = create_load_mapping_file_from_extract_declarations(
            decls, self.schema
        )
        with self.mapping_file.open("w") as f:
            yaml.safe_dump(mapping_data, f, sort_keys=False)

    @contextmanager
    def temp_extract_mapping(self, schema):
        with TemporaryDirectory() as t:
            t = Path(t)
            if self.extract_file.exists():
                f = self.extract_file
            else:
                f = StringIO(DEFAULT_EXTRACT_DATA)
            decls = ExtractRulesFile.parse_extract(f)

            extract_mapping = t / "extract.mapping.yml"
            with extract_mapping.open("w") as f:
                yaml.safe_dump(
                    create_extract_mapping_file_from_declarations(
                        list(decls.values()), schema
                    ),
                    f,
                )
            yield extract_mapping, decls

    def extract(self):
        with self.temp_extract_mapping(self.schema) as (extract_mapping, decls):
            task = _make_task(
                ExtractData,
                project_config=self.project_config,
                org_config=self.org_config,
                sql_path=self.data_file,
                mapping=str(extract_mapping),
            )
            task()
        self._save_load_mapping(list(decls.values()))
        return task.return_values

    def _snowfakery_dataload(self, recipe: Path) -> dict:
        subtask_config = TaskConfig(
            {"options": {**self.options, "recipe": str(recipe)}}
        )
        subtask = Snowfakery(
            project_config=self.project_config,
            task_config=subtask_config,
            org_config=self.org_config,
            flow=self.flow,
            name=self.name,
            stepnum=self.stepnum,
            logger=self.logger,
        )
        subtask()
        return subtask.return_values

    def load(self):
        if self.data_file.exists():
            self._sql_dataload()
        elif self.snowfakery_recipe.exists():
            self._snowfakery_dataload()
        else:  # pragma: no cover
            raise exc.BulkDataException(
                f"Dataset has no SQL ({self.data_file}) or recipe ({self.snowfakery_recipe})"
            )

    def _sql_dataload(self):

        task = _make_task(
            LoadData,
            project_config=self.project_config,
            org_config=self.org_config,
            sql_path=self.data_file,
            mapping=str(self.mapping_file),
        )
        task()

    def read_schema_subset(self) -> T.Dict[str, T.List[str]]:
        decls = ExtractRulesFile.parse_extract(self.extract_file)
        flattened = flatten_declarations(list(decls.values()), self.schema)
        return {obj.sf_object: obj.fields for obj in flattened}

    def read_which_fields_selected(self) -> T.Dict[str, T.Dict[str, bool]]:
        selected = self.read_schema_subset()
        selected_fields = {
            (obj, field) for obj, fields in selected.items() for field in fields
        }
        out = {}
        for objname, obj in self.schema.items():
            objrepr = out.setdefault(objname, {})
            for field in obj.fields.keys():
                is_selected = (objname, field) in selected_fields
                objrepr[field] = is_selected
        return out

    def update_schema_subset(self, objs: T.Dict[str, T.List[str]]):
        # TODO: Test round-tripping through this carefully...especially
        #       for weird objects like WorkBadgeDefinitions
        objs_dict = {name: {"fields": fields} for name, fields in objs.items()}
        with self.extract_file.open("w") as f:
            data = {"extract": objs_dict}
            yaml.safe_dump(data, f, sort_keys=False)
        decls = [
            SimplifiedExtractDeclaration(sf_object=name, fields=fields)
            for name, fields in objs.items()
        ]
        self._save_load_mapping(decls)


def _make_task(task_class, project_config, org_config, **options):
    task_config = TaskConfig({"options": options})
    return task_class(project_config, task_config, org_config)


DEFAULT_EXTRACT_DATA = """
extract:
    OBJECTS(ALL):
        fields: FIELDS(ALL)
"""
