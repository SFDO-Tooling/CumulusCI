import typing as T
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from io import StringIO
from logging import Logger, getLogger
from pathlib import Path
from shutil import rmtree
from tempfile import TemporaryDirectory

import yaml
from simple_salesforce import Salesforce

from cumulusci.core import exceptions as exc
from cumulusci.core.config import BaseProjectConfig, OrgConfig, TaskConfig
from cumulusci.salesforce_api.org_schema import Filters, Schema, get_org_schema
from cumulusci.tasks.bulkdata.convert_dataset_to_recipe import ConvertDatasetToRecipe
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
from cumulusci.utils.fileutils import backup

DEFAULT_LOGGER = getLogger(__file__)
ExtractTaskResults = TaskResults = dict


class DatasetFormat(Enum):
    snowfakery = "Snowfakery"
    sql = default = "Sql"


@dataclass
class Dataset:
    name: str
    project_config: BaseProjectConfig
    sf: Salesforce
    org_config: OrgConfig
    schema: T.Optional[Schema] = None
    initialized = False

    @property
    def path(self) -> Path:
        return Path(self.project_config.repo_root or "") / "datasets" / self.name

    @property
    def extract_file(self) -> Path:
        return self.path / f"{self.name}.extract.yml"

    @property
    def mapping_file(self) -> Path:
        return self.path / f"{self.name}.mapping.yml"

    @property
    def sql_file(self) -> Path:
        return self.path / f"{self.name}.dataset.sql"

    @property
    def snowfakery_recipe(self) -> Path:
        return self.path / f"{self.name}.dataset.yml"

    def exists(self) -> bool:
        return self.path.exists()

    def delete(self):
        rmtree(str(self.path))

    def __enter__(self, *args, **kwargs):
        if self.schema is None:
            self.schema_context = self._get_org_schema()
            self.schema = self.schema_context.__enter__(*args, **kwargs)  # type: ignore
        else:
            self.schema_context = None
        self.initialized = True
        return self

    def __exit__(self, *args, **kwargs):
        if self.schema_context:
            self.schema_context.__exit__(*args, **kwargs)  # type: ignore

    def create(self):
        assert (
            self.initialized
        ), "You must open this context manager. e.g. `with Dataset() as dataset`"

        if not self.path.exists():
            self.path.mkdir()

        self.extract_file.write_text(DEFAULT_EXTRACT_DATA)
        decls = ExtractRulesFile.parse_extract(StringIO(DEFAULT_EXTRACT_DATA))

        decls = list(decls.values())

    def _get_org_schema(self):
        return get_org_schema(
            self.sf,
            self.org_config,
            include_counts=True,
            filters=[Filters.extractable, Filters.createable, Filters.populated],
        )

    def _save_load_mapping(
        self,
        decls: T.Sequence[ExtractDeclaration],
        opt_in_only: T.Sequence[str] = (),
    ) -> None:
        assert isinstance(self.schema, Schema)
        mapping_data = create_load_mapping_file_from_extract_declarations(
            decls, self.schema, opt_in_only
        )
        with self.mapping_file.open("w") as f:
            yaml.safe_dump(mapping_data, f, sort_keys=False)

    @contextmanager
    def temp_extract_mapping(
        self,
        schema,
        extraction_definition: T.Optional[Path],
        opt_in_only: T.Sequence[str],
    ):
        with TemporaryDirectory() as t:
            t = Path(t)
            if extraction_definition:
                assert extraction_definition.exists(), "Cannot find extract mapping {f}"
                self.extract_file.write_text(extraction_definition.read_text())
            else:
                extraction_definition = self.extract_file

                if not self.extract_file.exists():  # pragma: no cover
                    self.extract_file.write_text(DEFAULT_EXTRACT_DATA)
            decls = ExtractRulesFile.parse_extract(extraction_definition)

            extract_mapping = t / "extract.mapping.yml"
            with extract_mapping.open("w") as f:
                yaml.safe_dump(
                    create_extract_mapping_file_from_declarations(
                        list(decls.values()), schema, opt_in_only
                    ),
                    f,
                )
            yield extract_mapping, decls

    def extract(
        self,
        options: T.Optional[T.Dict] = None,
        logger: T.Optional[Logger] = None,
        extraction_definition: T.Optional[Path] = None,
        opt_in_only: T.Sequence[str] = (),
        format: T.Optional[DatasetFormat] = DatasetFormat.default,
    ) -> ExtractTaskResults:
        ret = None
        options = options or {}
        logger = logger or DEFAULT_LOGGER
        format = format or DatasetFormat.default
        with self.temp_extract_mapping(
            self.schema, extraction_definition, opt_in_only
        ) as (
            extract_mapping,
            decls,
        ):
            if format == DatasetFormat.sql:
                ret = self.extract_as_sql(options, extract_mapping)
            elif format == DatasetFormat.snowfakery:
                ret = self.extract_as_recipe(
                    options, self.snowfakery_recipe, extract_mapping
                )
            else:  # pragma: no cov
                assert False, f"Strange format: {format}"
        self._save_load_mapping(list(decls.values()))
        return ret

    def extract_as_recipe(
        self, options: dict, recipe: Path, extract_mapping: Path
    ) -> TaskResults:
        with self.extract_as_temp_db(extract_mapping) as (sql_file, extract_ret):
            convert_ret = self._convert_dataset_to_recipe(options, sql_file, recipe)
        if self.sql_file.exists():
            backup(self.sql_file)
        return {"extract": extract_ret, "convert_dataset_to_recipe": convert_ret}

    def _convert_dataset_to_recipe(
        self, options: dict, db_path: Path, recipe: Path
    ) -> TaskResults:
        subtask = _make_task(
            ConvertDatasetToRecipe,
            project_config=self.project_config,
            org_config=self.org_config,
            database_url=f"sqlite:///{db_path}",
            recipe=recipe,
            **options,
        )
        subtask()
        return subtask.return_values

    @contextmanager
    def extract_as_temp_db(self, extract_mapping: Path):
        with TemporaryDirectory() as t:
            dir = Path(t)
            assert dir.exists()
            sql_file = Path(t) / "temporary_extract.db"
            assert dir.exists()
            ret = self.extract_as_db(extract_mapping, sql_file)
            yield sql_file, ret

    def extract_as_sql(
        self, options: dict, extract_mapping: Path
    ) -> ExtractTaskResults:
        task = _make_task(
            ExtractData,
            project_config=self.project_config,
            org_config=self.org_config,
            sql_path=self.sql_file,
            mapping=str(extract_mapping),
            **options,
        )
        task()
        if self.snowfakery_recipe.exists():
            backup(self.snowfakery_recipe)

        return task.return_values

    def extract_as_db(
        self, extract_mapping: Path, database_path: Path
    ) -> ExtractTaskResults:
        task = _make_task(
            ExtractData,
            project_config=self.project_config,
            org_config=self.org_config,
            database_url=f"sqlite:///{database_path.absolute()}",
            mapping=str(extract_mapping),
        )
        task()
        return task.return_values

    def _snowfakery_dataload(self, options: T.Dict, logger: Logger) -> TaskResults:
        options = {**options, "recipe": str(self.snowfakery_recipe)}

        subtask = _make_task(
            Snowfakery,
            project_config=self.project_config,
            org_config=self.org_config,
            logger=logger,
            **options,
        )
        subtask()
        return subtask.return_values

    def load(
        self, options: T.Optional[T.Dict] = None, logger: T.Optional[Logger] = None
    ) -> TaskResults:
        ret = None
        options = options or {}
        logger = logger or DEFAULT_LOGGER
        if self.sql_file.exists():
            ret = self._sql_dataload(options)
        elif self.snowfakery_recipe.exists():
            ret = self._snowfakery_dataload(options, logger)
        else:  # pragma: no cover
            raise exc.BulkDataException(
                f"Dataset has no SQL ({self.sql_file}) or recipe ({self.snowfakery_recipe})"
            )
        return ret

    def _sql_dataload(self, options: T.Dict) -> TaskResults:
        task = _make_task(
            LoadData,
            project_config=self.project_config,
            org_config=self.org_config,
            sql_path=self.sql_file,
            mapping=str(self.mapping_file),
            **options,
        )
        task()
        return task.return_values

    def read_schema_subset(self) -> T.Dict[str, T.List[str]]:
        assert isinstance(self.schema, Schema)
        decls = ExtractRulesFile.parse_extract(self.extract_file)
        flattened = flatten_declarations(list(decls.values()), self.schema)
        return {obj.sf_object: obj.fields for obj in flattened}  # type: ignore

    def read_which_fields_selected(self) -> T.Dict[str, T.Dict[str, bool]]:
        assert isinstance(self.schema, Schema)
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

    def update_schema_subset(
        self,
        objs: T.Dict[str, T.List[str]],
        opt_in_only: T.Sequence[str] = (),
    ):
        # TODO: Test round-tripping through this carefully...especially
        #       for weird objects like WorkBadgeDefinitions
        objs_dict = {name: {"fields": fields} for name, fields in objs.items()}
        with self.extract_file.open("w") as f:
            data = {"extract": objs_dict}
            yaml.safe_dump(data, f, sort_keys=False)
        decls = [
            SimplifiedExtractDeclaration(sf_object=name, fields=fields)  # type: ignore
            for name, fields in objs.items()
        ]
        self._save_load_mapping(decls, opt_in_only)


def _make_task(task_class, project_config, org_config, **options):
    task_config = TaskConfig({"options": options})
    return task_class(project_config, task_config, org_config)


DEFAULT_EXTRACT_DATA = """
extract:
    OBJECTS(ALL):
        fields: FIELDS(ALL)
"""
