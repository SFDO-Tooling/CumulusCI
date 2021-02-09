from tempfile import TemporaryDirectory
from pathlib import Path
from contextlib import ExitStack
from typing import NamedTuple
from sqlalchemy import create_engine

import sys
import time
from shutil import copyfile
from sarge import shell_quote

from subprocess import Popen

from cumulusci.core.tasks import BaseSalesforceTask
from cumulusci.tasks.bulkdata.generate_and_load_data_from_yaml import (
    GenerateAndLoadDataFromYaml,
)
from cumulusci.core.config import TaskConfig


bulkgen_task = "cumulusci.tasks.bulkdata.generate_from_yaml.GenerateDataFromYaml"


class SubProcTaskInfo(NamedTuple):
    working_directory: Path
    database_url: str
    proc: Popen

    def poll(self):
        return self.proc.poll()

    def wait(self):
        return self.proc.wait()

    def kill(self):
        return self.proc.kill()


class ParallelGenerateAndLoadFromRecipe(BaseSalesforceTask):
    """Generate and load data from Snowfakery in as many batches as necessary"""

    task_options = {
        **GenerateAndLoadDataFromYaml.task_options,
        "portion_size": {
            "description": "How many records to generate in a single group. Generally much larger than 50k.",
            "required": False,
        },
    }
    del task_options["data_generation_task"]
    task_options["num_records_tablename"]["required"] = True
    task_options["num_records"]["required"] = True

    def _init_options(self, kwargs):
        super()._init_options(kwargs)
        self.segment_size = self.options.get("segment_size", 50_000)
        self.num_records = int(self.options.get("num_records"))

    def _run_task(self, *args, **kwargs):
        with TemporaryDirectory() as shared_directory:
            shared_directory = Path(shared_directory)
            shared_db = Path(shared_directory) / "generated_data.db"
            sqlite_url = f"sqlite:///{shared_db}"
            self._initialize_common_data(shared_directory, sqlite_url)

            continuation_file = Path(shared_directory) / "continuation.yml"
            assert continuation_file.exists(), continuation_file
            shared_options = {
                "continuation_file": str(continuation_file),
                "num_records": self.segment_size,
                **self.options,
            }
            orgname = self.org_config.name
            self._generate_portions_in_parallel(
                orgname, shared_db, shared_options, self.num_records
            )

    def _generate_portions_in_parallel(
        self, orgname: str, shared_db: Path, shared_options: dict, num_records: int
    ):
        with ExitStack() as onexit:

            def subproc():
                portion_directory = onexit.enter_context(TemporaryDirectory())
                portion_directory = Path(portion_directory)
                assert portion_directory.exists()
                options = {**shared_options, "working_directory": portion_directory}
                return self._generate_portion(orgname, shared_db, options)

            subprocs = [subproc() for i in range(0, 5)]

            # this logic will need to be based on num_records.
            # open engines
            total = 0
            unfinished_procs = True
            num_records_tablename = shared_options["num_records_tablename"]
            finished_procs = []

            while total < num_records:
                time.sleep(1)
                newly_finished_procs = [
                    proc for proc in subprocs if proc.poll() is not None
                ]
                unfinished_procs = [proc for proc in subprocs if proc.poll() is None]
                for proc in newly_finished_procs:
                    finished_procs.append(proc)
                    if proc.poll() != 0:
                        assert 0, "Failed process"  # FXME
                        for proc2 in unfinished_procs:
                            proc2.kill()

                    total += self._check_count(proc, num_records_tablename)
                    unfinished_procs.append(subproc())

            # TODO: send a signal to the processes to finish up.
            #       probably through the creation of a filesystem file
            #       that they are looking for.
            for proc in unfinished_procs:
                proc.wait()

    def _check_count(self, proc: SubProcTaskInfo, num_records_tablename: str):
        engine = create_engine(proc.database_url)
        with engine.connect() as conn:
            num_records, *rest = next(
                conn.execute(f"select count(*) from {num_records_tablename}")
            )
            return num_records

    def _initialize_common_data(self, subdirectory: str, database_url: str):
        """Run the recipe once to initialize the IDs of "singleton objects" like GAUs and campaigns"""
        subtask_options = self.options.copy()
        subtask_options["num_records"] = None  # make the smallest batch possible
        subtask_options["working_directory"] = subdirectory
        subtask_options["database_url"] = database_url
        task_config = TaskConfig({"options": subtask_options})
        initial_subtask = GenerateAndLoadDataFromYaml(
            self.project_config, task_config, org_config=self.org_config
        )
        initial_subtask()

    def _generate_portion(
        self,
        orgname: str,
        parent_db: Path,
        options: dict,
    ):
        working_directory = Path(options["working_directory"])
        database_file = working_directory / "generated_data.db"
        copyfile(parent_db, database_file)
        database_url = f"sqlite:///{database_file}"
        options = {
            **options,
            "working_directory": str(working_directory),
            "database_url": database_url,
            "num_records": self.options["portion_size"],
            "reset_oids": "True",
            "replace_database": "True",
        }
        if options.get("debug_before") is not None:
            del options["debug_before"]
        if options.get("debug_after") is not None:
            del options["debug_after"]
        if options.get("no_prompt") is not None:
            del options["no_prompt"]
        if options.get("portion_size") is not None:
            del options["portion_size"]
        print("ZZZXXX", options)
        proc = _execute_cci_task_out_of_process(
            "generate_and_load_from_yaml", options, orgname
        )
        cmdline = " ".join([shell_quote(s) for s in proc.args])
        self.logger.info(
            f"Creating subprocess: {cmdline} # (note that escaping is not necessary in this context)"
        )
        return SubProcTaskInfo(working_directory, database_url, proc)


# TODO: make this a util
def _execute_cci_task_out_of_process(taskname: str, options: dict, orgname: str):
    cmd = [sys.executable, "-m", "cumulusci", "task", "run", taskname, "--org", orgname]
    pairwise_options = [(f"--{key}", value) for key, value in options.items()]
    flattened_options = [item for sublist in pairwise_options for item in sublist]
    cmd.extend(flattened_options)
    try:
        return Popen(cmd)
    except Exception as e:
        raise Exception(cmd, *e.args)
