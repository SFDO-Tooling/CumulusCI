import shutil
import time
import queue
import typing as T

from pathlib import Path
from multiprocessing import Process, Value
from cumulusci.utils.parallel.queue_workaround import MyQueue, SharedCounter
from contextlib import contextmanager
import logging
import coloredlogs
from tempfile import TemporaryDirectory


from cumulusci.tasks.bulkdata.generate_from_yaml import GenerateDataFromYaml
from cumulusci.tasks.bulkdata.load import LoadData
from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.tasks.bulkdata.generate_and_load_data_from_yaml import (
    GenerateAndLoadDataFromYaml,
)
from cumulusci.core.config import TaskConfig
from cumulusci.cli.logger import init_logger

bulkgen_task = "cumulusci.tasks.bulkdata.generate_from_yaml.GenerateDataFromYaml"


class SnowScale(BaseSalesforceApiTask):
    """ """

    task_docs = """
    """
    task_options = {
        "recipe": {},
        "num_generator_workers": {},
        "num_uploader_workers": {},
        "loading_rules": {},  # TODO: Impl, Docs
        "working_directory": {},  # TODO: Impl, Docs
        "recipe_options": {},  # TODO: Impl, Docs
        "num_records": {},  # TODO: Docs
        "num_records_tablename": {},  # TODO : Better name
        "max_batch_size": {},  # TODO Impl, Docs
    }

    def _init_options(self, kwargs):
        args = {"data_generation_task": bulkgen_task, **kwargs}

        super()._init_options(args)

    def _validate_options(self):
        # long-term solution: psutil.cpu_count(logical=False)
        self.num_generator_workers = int(self.options.get("num_generator_workers", 4))
        self.num_uploader_workers = int(self.options.get("num_uploader_workers", 25))
        # self.num_uploader_workers = 3  # FIXME
        # Do not store recipe due to MetaDeploy options freezing
        recipe = Path(self.options.get("recipe"))
        assert recipe.exists()
        assert isinstance(self.options.get("num_records_tablename"), str)

    def _run_task(self):
        self._done = Value("i", False)
        self.max_batch_size = self.options.get("max_batch_size", 250_000)
        self.dynamic_max_batch_size = Value(
            "i",
        )
        self.recipe = Path(self.options.get("recipe"))
        self.upload_queue = MyQueue()
        self.job_counter = SharedCounter(0)
        working_directory = self.options.get("working_directory")
        if working_directory:
            working_directory = Path(working_directory)
        with self._generate_and_load_initial_batch(working_directory) as (
            tempdir,
            template_path,
        ):
            self.logger.info(f"Working directory is {tempdir}")
            # os.system(f"code {tempdir}")  # FIXME
            assert tempdir.exists()
            self.generators_path = Path(tempdir) / "1_generators"
            self.generators_path.mkdir()
            self.queue_for_loading_directory = Path(tempdir) / "2_load_queue"
            self.queue_for_loading_directory.mkdir()
            self.loaders_path = Path(tempdir) / "3_loaders"
            self.loaders_path.mkdir()
            self.archive_directory = Path(tempdir, "4_finished")
            self.archive_directory.mkdir()

            def new_generate_process(idx):
                idx = idx + 1  # use 1-based indexing
                args = [
                    self.generators_path / str(idx),
                    template_path,
                    idx,
                ]
                return Process(target=self._generate_process, args=args)

            def new_upload_process(idx):
                idx = idx + 1  # use 1-based indexing
                args = [self.loaders_path, idx]
                return Process(target=self._load_process, args=args)

            generator_workers = self._spawn_processes(
                new_generate_process, self.num_generator_workers
            )
            uploader_workers = self._spawn_processes(
                new_upload_process, self.num_uploader_workers
            )
            for (
                max_batch_size,
                rows_remaining,
                rows_in_flight,
            ) in self.generate_max_batch_sizes():
                time.sleep(10)
                self.dynamic_max_batch_size.value = min(max_batch_size, 250_000)
                print(
                    "********** PROGRESS *********",
                )
                print(
                    "Rows Remaining",
                    rows_remaining,
                    "Rows in flight",
                    rows_in_flight,
                    "Dynamic max batch size",
                    self.dynamic_max_batch_size.value,
                )
                print(tempdir)
            print("WAS DONE")
            self._done.value = True

            # TODO: Perhaps need a timeout and kill?
            for worker in generator_workers:
                worker.join()

            for worker in uploader_workers:
                worker.join()

            print("DONE!!!!")  # FIXME

            # for worker in num_uploader_workers:
            #     num_uploader_workers.join()

    @staticmethod
    def _spawn_processes(func, number):
        processes = list(map(func, range(number)))
        for process in processes:
            process.start()
        return processes

    def _generate_process(
        self, working_parent_dir: Path, template_path: Path, worker_idx: int
    ):
        working_parent_dir.mkdir(exist_ok=True)
        batch_size = 5000
        while not self.done():  # FIXME
            increased_batch_size = False
            while (
                self.upload_queue.qsize() > self.num_uploader_workers
                and not self.done()
            ):
                print(f"Waiting due to queue size of {self.upload_queue.qsize()}")
                if not increased_batch_size:
                    batch_size = min(
                        batch_size * 2,
                        self.dynamic_max_batch_size.value,
                        self.max_batch_size,
                    )
                    increased_batch_size = True
                    print(f"Expanding batch_size to {batch_size}")
                time.sleep(60)
            idx = self.job_counter.increment()
            working_dir = working_parent_dir / (str(idx) + "_" + str(batch_size))
            shutil.copytree(template_path, working_dir)
            database_file = working_dir / "generated_data.db"
            # not needed once just_once is implemented
            mapping_file = working_dir / "temp_mapping.yml"
            database_url = f"sqlite:///{database_file}"
            # f"{working_directory}/continuation.yml"
            assert working_dir.exists()
            options = {
                **self.options,
                "generator_yaml": str(self.recipe),
                "database_url": database_url,
                "working_directory": working_dir,
                "num_records": batch_size,  # FIXME
                "generate_mapping_file": mapping_file,
                # continuation_file =       # FIXME
            }
            self._invoke_subtask(GenerateDataFromYaml, options, working_dir)
            assert mapping_file.exists()
            outdir = shutil.move(working_dir, self.queue_for_loading_directory)
            self.upload_queue.put(outdir)

    def _load_process(self, working_parent_dir: Path, worker_idx: int):
        working_parent_dir.mkdir(exist_ok=True)
        while not self.done():
            try:
                generator_working_directory = self.upload_queue.get(block=False)
            except queue.Empty:
                generator_working_directory = None
                time.sleep(10)
            if generator_working_directory:
                working_directory = shutil.move(
                    generator_working_directory, working_parent_dir
                )
                working_directory = Path(working_directory)
                mapping_file = working_directory / "temp_mapping.yml"
                database_file = working_directory / "generated_data.db"
                assert mapping_file.exists(), mapping_file
                assert database_file.exists(), database_file
                database_url = f"sqlite:///{database_file}"

                options = {
                    "mapping": mapping_file,
                    "reset_oids": False,
                    "database_url": database_url,
                }
                self._invoke_subtask(LoadData, options, working_directory)
                shutil.move(working_directory, self.archive_directory)

    def _invoke_subtask(
        self, TaskClass: type, subtask_options: T.Mapping[str, T.Any], working_dir: Path
    ):
        subtask_config = TaskConfig({"options": subtask_options})
        subtask = TaskClass(
            project_config=self.project_config,
            task_config=subtask_config,
            org_config=self.org_config,
            flow=self.flow,
            name=self.name,
            stepnum=self.stepnum,
        )
        with self._add_tempfile_logger(working_dir / f"{TaskClass.__name__}.log"):
            try:
                subtask()
            except Exception as e:
                print("Exception DONE", TaskClass.__name__, e)
                self._done.value = True
                raise e

    def done(self):
        if self._done.value:
            return True

    def rows_in_flight(self):
        dirs = [
            self.generators_path,
            self.queue_for_loading_directory,
            self.loaders_path,
        ]

        total_inflight_records = 0

        for dir in dirs:
            subdirs = dir.glob("*_*")
            for subdir in subdirs:
                idx, count = subdir.name.split("_")
                total_inflight_records += int(count)

        return total_inflight_records

    from pysnooper import snoop

    @snoop()
    def generate_max_batch_sizes(self):
        batch_size = 1
        while batch_size > 0:
            target_number = int(self.options.get("num_records"))
            rows_in_flight = self.rows_in_flight()
            count = self.get_org_record_count()
            rows_remaining = target_number - (count + rows_in_flight)
            rows_remaining = max(rows_remaining, 0)
            batch_size = rows_remaining // (self.num_generator_workers * 2)
            yield batch_size, rows_remaining, rows_in_flight

    def get_org_record_count(self):
        sobject = self.options.get("num_records_tablename")
        query = f"select count(Id) from {sobject}"
        count = self.sf.query(query)["records"][0]["expr0"]
        return int(count)
        # I'll probably need this code when I hit big orgs

        # data = self.sf.restful(f"limits/recordCount?sObjects={table}")
        # count = int(data["sObjects"][0]["count"])

    @contextmanager
    def workingdir_or_tempdir(self, working_directory: T.Optional[Path]):
        if working_directory:
            working_directory.mkdir()
            yield working_directory
        else:
            with TemporaryDirectory() as tempdir:
                yield tempdir

    @contextmanager
    def _generate_and_load_initial_batch(
        self, working_directory: T.Optional[Path]
    ) -> Path:
        with self.workingdir_or_tempdir(working_directory) as tempdir:
            template_dir = Path(tempdir) / "template"
            template_dir.mkdir()
            # FIXME:
            # self._generate_and_load_batch(template_dir, {"num_records": 1})
            yield Path(tempdir), template_dir

    def _generate_and_load_batch(self, tempdir, options) -> Path:
        options = {**self.options, **options, "working_directory": tempdir}
        self._invoke_subtask(GenerateAndLoadDataFromYaml, options, tempdir)

    @contextmanager
    def _add_tempfile_logger(self, my_log: Path):
        init_logger()
        rootLogger = logging.getLogger("cumulusci")
        with open(my_log, "w") as f:
            handler = logging.StreamHandler(stream=f)
            handler.setLevel(logging.DEBUG)
            formatter = coloredlogs.ColoredFormatter(fmt="%(asctime)s: %(message)s")
            handler.setFormatter(formatter)

            rootLogger.addHandler(handler)
            try:
                yield f
            finally:
                rootLogger.removeHandler(handler)
