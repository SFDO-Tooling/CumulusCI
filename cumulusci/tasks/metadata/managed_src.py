from distutils.dir_util import copy_tree, remove_tree
from pathlib import Path

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.tasks import BaseTask
from cumulusci.utils import find_replace


class CreateManagedSrc(BaseTask):
    task_docs = """
        Apex classes which use the @deprecated annotation can comment
        it out using //cumulusci-managed so that it can be deployed as
        part of unmanaged metadata, where this annotation is not allowed.
        This task is for use when deploying to a packaging org to
        remove the comment so that the annotation takes effect.
    """

    task_options = {
        "path": {
            "description": "The path containing metadata to process for managed deployment",
            "required": True,
        },
        "revert_path": {
            "description": "The path to copy the original metadata to for the revert call",
            "required": True,
        },
    }

    managed_token = "//cumulusci-managed"

    def _run_task(self):
        # Check that path exists
        path = Path(self.options["path"])
        if not path.is_dir():
            raise TaskOptionsError(
                f"The path {path} does not exist or is not a directory"
            )

        # Check that revert_path does not exist
        revert_path = Path(self.options["revert_path"])
        if revert_path.exists():
            raise TaskOptionsError(
                f"The revert_path {self.options['revert_path']} already exists.  Delete it and try again"
            )

        # Copy path to revert_path
        copy_tree(str(path), str(revert_path))

        # Edit metadata in path
        self.logger.info(
            f"Removing the string {self.managed_token} from {path}/classes and {path}/triggers"
        )
        find_replace(
            self.managed_token,
            "",
            str(path / "classes"),
            "*.cls",
            self.logger,
        )
        find_replace(
            self.managed_token,
            "",
            str(path / "triggers"),
            "*.trigger",
            self.logger,
        )

        self.logger.info(
            f"{self.managed_token} has been stripped from all classes and triggers in {path}"
        )


class RevertManagedSrc(BaseTask):
    task_options = {
        "path": {
            "description": "The path containing metadata to process for managed deployment",
            "required": True,
        },
        "revert_path": {
            "description": "The path to copy the original metadata to for the revert call",
            "required": True,
        },
    }

    def _run_task(self):
        path = Path(self.options["path"])
        revert_path = Path(self.options["revert_path"])
        # Check that revert_path does exists
        if not revert_path.is_dir():
            raise TaskOptionsError(
                f"The revert_path {revert_path} does not exist or is not a directory"
            )

        self.logger.info(f"Reverting {path} from {revert_path}")
        copy_tree(str(revert_path), str(path), update=1)
        self.logger.info(f"{path} is now reverted")

        # Delete the revert_path
        self.logger.info(f"Deleting {str(revert_path)}")
        remove_tree(revert_path)
