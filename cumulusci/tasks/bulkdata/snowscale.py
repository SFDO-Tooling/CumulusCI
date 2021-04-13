import shutil
import time
import typing as T

from pathlib import Path
from multiprocessing import Process, Value
from tempfile import TemporaryDirectory
from contextlib import contextmanager, redirect_stdout, redirect_stderr
from dataclasses import dataclass

from cumulusci.utils.parallel.queue_workaround import SharedCounter
from cumulusci.tasks.bulkdata.generate_from_yaml import GenerateDataFromYaml
from cumulusci.tasks.bulkdata.load import LoadData
from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.tasks.bulkdata.generate_and_load_data_from_yaml import (
    GenerateAndLoadDataFromYaml,
)
from cumulusci.core.config import TaskConfig
from cumulusci.cli.logger import init_logger

bulkgen_task = "cumulusci.tasks.bulkdata.generate_from_yaml.GenerateDataFromYaml"


@dataclass
class UploadStatus:
    confirmed_count_in_org: int
    rows_being_generated: int
    rows_queued: int
    rows_being_loaded: int
    target_count: int
    base_batch_size: int
    delay_mutiple: int
    upload_queue_size: int
    user_max_num_uploader_workers: int
    user_max_num_generator_workers: int

    @property
    def max_needed_generators(self):
        return max(self.user_max_num_uploader_workers - self.upload_queue_size, 0)

    @property
    def total_needed_generators(self):
        return min(self.user_max_num_generator_workers, self.max_needed_generators)

    @property
    def total_in_flight(self):
        return self.rows_being_generated + self.rows_queued + self.rows_being_loaded

    @property
    def maximum_estimated_count_so_far(self):
        return self.confirmed_count_in_org + self.total_in_flight

    @property
    def min_rows_remaining(self):
        return max(0, self.target_count - self.maximum_estimated_count_so_far)

    @property
    def mode(self):
        if self.min_rows_remaining:
            return "Parallel"
        else:
            # when the rows in-flight are sufficient to fill the
            # org, stop the parallel processing mode and switch
            # to a Serial mode which is easier to monitor to
            # try and hit our goal size
            return "Serial"

    @property
    def batch_size(self):
        return self.base_batch_size * self.delay_mutiple


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
        self.num_uploader_workers = int(self.options.get("num_uploader_workers", 15))
        # self.num_uploader_workers = 3  # FIXME
        # Do not store recipe due to MetaDeploy options freezing
        recipe = Path(self.options.get("recipe"))
        assert recipe.exists()
        assert isinstance(self.options.get("num_records_tablename"), str)

    def _run_task(self):
        print("A")
        self._done = Value("i", False)
        print("B")
        self.max_batch_size = self.options.get("max_batch_size", 250_000)
        self.recipe = Path(self.options.get("recipe"))
        self.job_counter = SharedCounter(0)
        self.delay_multiple = SharedCounter(1)

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

            self._loop(template_path, tempdir)

            self._done.value = True

            print("DONE!!!!")  # FIXME

    def _loop(self, template_path, tempdir):
        self._parallelized_loop(template_path, tempdir)
        self._serial_loop(template_path, tempdir)

    def _parallelized_loop(self, template_path, tempdir):
        generator_workers = []
        upload_workers = []

        upload_status = self.generate_upload_status()
        print(upload_status)
        while upload_status.mode == "Parallel":
            print(
                "********** PROGRESS *********",
            )
            print(upload_status)
            upload_workers = self._spawn_transient_upload_workers(upload_workers)
            generator_workers = [
                worker for worker in generator_workers if worker.is_alive()
            ]

            if upload_status.upload_queue_size > self.num_uploader_workers:
                print("WAITING FOR UPLOAD QUEUE TO CATCH UP")
                self.delay_multiple.increment()
                print(f"Batch size multiple={self.delay_multiple.value}")
            else:
                generator_workers = self._spawn_transient_generator_workers(
                    generator_workers, upload_status, template_path
                )
            print("Workers:", len(generator_workers), len(upload_workers))
            print("Queue size", upload_status.upload_queue_size)
            time.sleep(3)
            upload_status = self.generate_upload_status()

            print(tempdir)

        for worker in generator_workers:
            worker.join()
        for worker in upload_workers:
            worker.join()

    def _serial_loop(self, template_path, tempdir):
        assert 0, "NotImpl"

    def _spawn_transient_upload_workers(self, upload_workers):
        upload_workers = [worker for worker in upload_workers if worker.is_alive()]
        current_upload_workers = len(upload_workers)
        if current_upload_workers < self.num_uploader_workers:
            free_workers = self.num_uploader_workers - current_upload_workers
            jobs_to_be_done = list(self.queue_for_loading_directory.glob("*_*"))
            jobs_to_be_done.sort(key=lambda j: int(j.name.split("_")[0]))

            jobs_to_be_done = jobs_to_be_done[0:free_workers]
            for job in jobs_to_be_done:
                process = Process(target=self._load_process, args=[job])
                # add an error trapping/reporting wrapper
                process.start()
                upload_workers.append(process)
        return upload_workers

    def _spawn_transient_generator_workers(self, workers, upload_status, template_path):
        workers = [worker for worker in workers if worker.is_alive()]
        # TODO: Check for errors!!!

        total_needed_workers = upload_status.total_needed_generators
        new_workers = total_needed_workers - len(workers)

        for idx in range(new_workers):
            args = [
                self.generators_path,
                upload_status.batch_size,
                template_path,
                idx,
            ]
            process = Process(target=self._do_generate, args=args)
            # add an error trapping/reporting wrapper
            process.start()

            workers.append(process)
        return workers

    # def _generate_process(
    #     self,
    #     working_parent_dir: Path,
    #     template_path: Path,
    #     batch_size: int,
    #     worker_idx: int,
    # ):
    #     working_parent_dir.mkdir(exist_ok=True)
    #     self._do_generate(working_parent_dir, batch_size, template_path)
    # batch_size = 5000
    # while not self.done():  # FIXME
    #     increased_batch_size = False
    #     while (
    #         self.upload_queue.qsize() > self.num_uploader_workers
    #         and not self.done()
    #     ):
    #         print(f"Waiting due to queue size of {self.upload_queue.qsize()}")
    #         if not increased_batch_size:
    #             self.delay_multiple = self.delay_multiple + 1
    #             increased_batch_size = True
    #             print(f"Expanding batch_size to {batch_size}")
    #         time.sleep(60)
    #         self._do_generate(working_parent_dir, batch_size, template_path)

    def _do_generate(self, working_parent_dir, batch_size, template_path, idx: int):
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
            "num_records": batch_size,
            "generate_mapping_file": mapping_file,
            # continuation_file =       # FIXME
        }
        self._invoke_subtask(GenerateDataFromYaml, options, working_dir)
        assert mapping_file.exists()
        shutil.move(working_dir, self.queue_for_loading_directory)

    def _load_process(self, job_directory: Path):
        working_parent_dir = self.loaders_path
        working_parent_dir.mkdir(exist_ok=True)
        working_directory = shutil.move(job_directory, working_parent_dir)
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

    def rows_in_dir(self, dir):
        idx_and_counts = (subdir.name.split("_") for subdir in dir.glob("*_*"))
        return sum(int(count) for (idx, count) in idx_and_counts)

    def generate_upload_status(self):
        return UploadStatus(
            confirmed_count_in_org=self.get_org_record_count(),
            target_count=int(self.options.get("num_records")),
            rows_being_generated=self.rows_in_dir(self.generators_path),
            rows_queued=self.rows_in_dir(self.queue_for_loading_directory),
            delay_mutiple=self.delay_multiple.value,
            # note that these may count as already imported in the org
            rows_being_loaded=self.rows_in_dir(self.loaders_path),
            upload_queue_size=sum(
                1 for dir in self.queue_for_loading_directory.glob("*_*")
            ),
            base_batch_size=5000,  # FIXME
            user_max_num_uploader_workers=self.num_uploader_workers,
            user_max_num_generator_workers=self.num_generator_workers,
        )

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
        # rootLogger = logging.getLogger("cumulusci")
        with open(my_log, "w") as f:
            with (redirect_stdout(f), redirect_stderr(f)):
                init_logger()
                yield f
            # handler = logging.StreamHandler(stream=f)
            # handler.setLevel(logging.DEBUG)
            # formatter = coloredlogs.ColoredFormatter(fmt="%(asctime)s: %(message)s")
            # handler.setFormatter(formatter)

            # rootLogger.addHandler(handler)
            # try:
            #     yield f
            # finally:
            #     rootLogger.removeHandler(handler)
