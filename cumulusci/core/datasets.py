import typing as T
from contextlib import contextmanager
from dataclasses import dataclass
from io import StringIO
from logging import Logger, getLogger
from pathlib import Path
from shutil import rmtree
from tempfile import TemporaryDirectory

import yaml
from simple_salesforce import Salesforce
from snowfakery.cci_mapping_files.declaration_parser import (
    SObjectRuleDeclaration,
    SObjectRuleDeclarationFile,
)

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

DEFAULT_LOGGER = getLogger(__file__)


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
    def load_rules_file(self) -> Path:
        # to be merged into the mapping file when it is created on extract
        return self.path / f"{self.name}.load.yml"

    @property
    def mapping_file(self) -> Path:
        return self.path / f"{self.name}.mapping.yml"

    @property
    def data_file(self) -> Path:
        return self.path / f"{self.name}.dataset.sql"

    @property
    def snowfakery_recipe(self) -> Path:
        return self.path / f"{self.name}.recipe.yml"

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
        loading_rules: T.Sequence[SObjectRuleDeclaration] = (),
    ) -> None:
        assert isinstance(self.schema, Schema)
        mapping_data = create_load_mapping_file_from_extract_declarations(
            decls, self.schema, opt_in_only, loading_rules
        )
        with self.mapping_file.open("w") as f:
            f.write(EDIT_MAPPING_WARNING)
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
        loading_rules_file: T.Optional[Path] = None,
    ):
        options = options or {}
        logger = logger or DEFAULT_LOGGER
        with self.temp_extract_mapping(
            self.schema, extraction_definition, opt_in_only
        ) as (
            extract_mapping,
            decls,
        ):
            task = _make_task(
                ExtractData,
                project_config=self.project_config,
                org_config=self.org_config,
                sql_path=self.data_file,
                mapping=str(extract_mapping),
            )
            task()
        loading_rules = self._parse_loading_rules_file(loading_rules_file)

        self._save_load_mapping(list(decls.values()), opt_in_only, loading_rules)
        return task.return_values

    def _parse_loading_rules_file(
        self, loading_rules_file: T.Optional[Path]
    ) -> T.List[SObjectRuleDeclaration]:
        """Parse a loading rules file if provided, else try to parse
        <datasets/dataset/dataset.load.yml>"""
        if loading_rules_file:
            assert loading_rules_file.exists()
        else:
            if self.load_rules_file.exists():
                loading_rules_file = self.load_rules_file

        if loading_rules_file:
            with loading_rules_file.open() as f:
                parse_result = SObjectRuleDeclarationFile.parse_from_yaml(f)
                loading_rules = parse_result.sobject_declarations
        else:
            loading_rules = []

        return loading_rules

    def _snowfakery_dataload(self, options: T.Dict, logger: Logger) -> T.Dict:
        subtask_config = TaskConfig(
            {"options": {**options, "recipe": str(self.snowfakery_recipe)}}
        )
        subtask = Snowfakery(
            project_config=self.project_config,
            task_config=subtask_config,
            org_config=self.org_config,
            logger=logger,
        )
        subtask()
        return subtask.return_values

    def load(
        self, options: T.Optional[T.Dict] = None, logger: T.Optional[Logger] = None
    ):
        options = options or {}
        logger = logger or DEFAULT_LOGGER
        if self.data_file.exists():
            self._sql_dataload(options)
        elif self.snowfakery_recipe.exists():
            self._snowfakery_dataload(options, logger)
        else:  # pragma: no cover
            raise exc.BulkDataException(
                f"Dataset has no SQL ({self.data_file}) "
                "or recipe ({self.snowfakery_recipe})"
            )

    def _sql_dataload(self, options: T.Dict):

        task = _make_task(
            LoadData,
            project_config=self.project_config,
            org_config=self.org_config,
            sql_path=self.data_file,
            mapping=str(self.mapping_file),
            **options,
        )
        task()

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
            SimplifiedExtractDeclaration(sf_object=name, fields=fields)
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

EDIT_MAPPING_WARNING = """# Editing this file is usually not recommended because it will
# be overwritten the next time you re-capture this data.
#
# You can change this file's contents permanently by creating a
# .load.yml file and re-capturing:
#
#  https://cumulusci.readthedocs.io/en/stable/data.html#extracting-and-loading-sample-datasets
"""
