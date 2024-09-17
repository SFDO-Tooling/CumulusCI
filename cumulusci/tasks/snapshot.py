import json
import os
import time
from datetime import datetime, timedelta
from dateutil.parser import parse
from cumulusci.core.exceptions import CumulusCIException, SalesforceException
from cumulusci.core.sfdx import sfdx
from cumulusci.core.utils import process_bool_arg
from cumulusci.salesforce_api.utils import get_simple_salesforce_connection
from cumulusci.tasks.salesforce import BaseSalesforceTask
from cumulusci.tasks.github.base import BaseGithubTask
from github3 import GitHubError
from pydantic import BaseModel, Field, validator
from simple_salesforce import Salesforce
from simple_salesforce.exceptions import SalesforceResourceNotFound
from rich.console import Console
from rich.table import Table

ORG_SNAPSHOT_FIELDS = [
    "Id",
    "SnapshotName",
    "Description",
    "Status",
    "SourceOrg",
    "CreatedDate",
    "LastModifiedDate",
    "ExpirationDate",
    "Error",
]


import time
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TimeElapsedColumn,
)
from rich.panel import Panel
from rich.live import Live


class SnapshotNameValidator(BaseModel):
    base_name: str = Field(..., max_length=13)

    @classmethod
    @validator("base_name")
    def validate_name(cls, name):
        if len(name) > 13:
            raise ValueError("Snapshot name cannot exceed 13 characters")
        if not name.isalnum():
            raise ValueError("Snapshot name must only contain alphanumeric characters")
        return name


class SnapshotManager:
    def __init__(self, devhub, logger):
        self.devhub = devhub
        self.logger = logger
        self.existing_active_snapshot_id = None
        self.temporary_snapshot_name = None
        self.console = Console()

    def generate_temp_name(self, base_name: str, max_length: int = 14) -> str:
        temp_name = f"{base_name}0"
        if len(temp_name) > max_length:
            temp_name = temp_name[:max_length]
        self.logger.info(f"Generated temporary snapshot name: {temp_name}")
        return temp_name

    def query_existing_active_snapshot(self, snapshot_name: str):
        self.logger.info(
            f"Checking for existing active snapshot with name: {snapshot_name}"
        )
        query = f"SELECT Id FROM OrgSnapshot WHERE Status = 'Active' AND SnapshotName = '{snapshot_name}'"
        result = self.devhub.query(query)

        if result["totalSize"] > 0:
            self.existing_active_snapshot_id = result["records"][0]["Id"]
            self.logger.info(
                f"Found existing active snapshot: {self.existing_active_snapshot_id}"
            )
        else:
            self.logger.info(f"No active snapshot found with name {snapshot_name}")

    def query_and_delete_in_progress_snapshot(self, snapshot_name: str):
        self.logger.info(
            f"Checking for in-progress snapshot with name: {snapshot_name}"
        )
        query = f"SELECT Id FROM OrgSnapshot WHERE Status in ('Active','InProgress') AND SnapshotName = '{snapshot_name}'"
        result = self.devhub.query(query)

        if result["totalSize"] > 0:
            snapshot_id = result["records"][0]["Id"]
            self.logger.info(
                f"Found in-progress snapshot {snapshot_id}, deleting it..."
            )
            self.devhub.OrgSnapshot.delete(snapshot_id)
            self.logger.info(f"Deleted in-progress snapshot: {snapshot_id}")
        else:
            self.logger.info(f"No in-progress snapshot found with name {snapshot_name}")

    def create_org_snapshot(
        self, snapshot_name: str, description: str, source_org: str
    ):
        self.logger.info(f"Creating new org snapshot: {snapshot_name}")
        snapshot_body = {
            "Description": description,
            "SnapshotName": snapshot_name,
            "SourceOrg": source_org,
            "Content": "metadatadata",
        }
        try:
            snapshot_result = self.devhub.OrgSnapshot.create(snapshot_body)
            snapshot_id = snapshot_result["id"]
            self.logger.info(f"Org snapshot {snapshot_id} created.")
            return snapshot_id
        except SalesforceException as e:
            if "NOT_FOUND" in str(e):
                raise SnapshotError(
                    "Org snapshot feature is not enabled for this Dev Hub."
                ) from e
            raise

    def poll_for_completion(
        self,
        snapshot_id: str,
        progress,
        task,
        timeout: int = 1200,
        initial_poll_interval: int = 10,
    ):
        poll_interval = initial_poll_interval
        start_time = time.time()
        end_time = start_time + timeout

        while time.time() < end_time:
            try:
                snapshot = self.devhub.OrgSnapshot.get(snapshot_id)
            except SalesforceResourceNotFound as exc:
                raise SnapshotError(
                    "Snapshot not found. This usually happens because another build deleted the snapshot while it was being built."
                ) from exc

            status = snapshot.get("Status")
            progress.update(
                task, description=f"[cyan]Creating snapshot... Status: {status}"
            )

            if status == "Active":
                progress.update(task, completed=100)
                self.logger.info(f"Snapshot {snapshot_id} completed successfully.")
                return snapshot
            if status == "Error":
                progress.update(task, completed=100)
                raise SnapshotError(
                    f"Snapshot {snapshot_id} failed to complete. Error: {snapshot.get('Error')}"
                )

            time.sleep(poll_interval)
            elapsed = time.time() - start_time
            progress.update(task, completed=min(int((elapsed / timeout) * 100), 100))
            poll_interval = min(poll_interval * 1.5, 30)

        raise TimeoutError(
            f"Snapshot {snapshot_id} did not complete within {timeout} seconds."
        )

    def delete_snapshot(self, snapshot_id: str = None):
        snapshot_id = snapshot_id or self.existing_active_snapshot_id
        if snapshot_id:
            self.logger.info(f"Deleting snapshot: {snapshot_id}")
            self.devhub.OrgSnapshot.delete(snapshot_id)
            self.logger.info(f"Deleted snapshot: {snapshot_id}")

    def rename_snapshot(self, snapshot_id: str, new_name: str):
        self.logger.info(f"Renaming snapshot {snapshot_id} to {new_name}")
        update_body = {"SnapshotName": new_name}
        self.devhub.OrgSnapshot.update(snapshot_id, update_body)
        self.logger.info(f"Snapshot {snapshot_id} renamed to {new_name}")

    def update_snapshot_from_org(
        self, base_name: str, description: str, source_org: str, wait: bool = True
    ):
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=self.console,
        ) as progress:
            task = progress.add_task("[green]Creating snapshot", total=100)

            # Step 1: Generate temporary name (5% progress)
            progress.update(
                task, advance=5, description="[green]Generating temporary name"
            )
            temp_name = self.generate_temp_name(base_name)

            # Step 2: Check for existing snapshots (10% progress)
            progress.update(
                task, advance=5, description="[green]Checking for existing snapshots"
            )
            self.query_existing_active_snapshot(base_name)
            self.query_and_delete_in_progress_snapshot(temp_name)

            # Step 3: Create new snapshot (10% progress)
            progress.update(
                task, advance=10, description="[green]Creating new snapshot"
            )
            snapshot_id = self.create_org_snapshot(temp_name, description, source_org)

            if not wait:
                snapshot = self.devhub.OrgSnapshot.get(snapshot_id)
                return snapshot

            # Step 4: Wait for snapshot to complete (60% progress)
            progress.update(task, description="[green]Waiting for snapshot to complete")
            snapshot = self.poll_for_completion(snapshot_id, progress, task)

            # Step 5: Finalize snapshot (10% progress)
            progress.update(task, advance=10, description="[green]Finalizing snapshot")
            self.delete_snapshot()  # Deletes the existing active snapshot if it exists
            self.rename_snapshot(snapshot_id, base_name)

        self.console.print(
            Panel(
                f"Snapshot {snapshot_id} created successfully!",
                title="Snapshot Creation",
                border_style="green",
            )
        )
        self.logger.info(f"Snapshot management complete for {snapshot_id}")
        return snapshot

    def finalize_temp_snapshot(
        self, snapshot_name: str, description: str, snapshot_id: str
    ):
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=self.console,
        ) as progress:
            task = progress.add_task("[green]Creating snapshot", total=100)

            # Step 1: Check for existing snapshots (10% progress)
            progress.update(
                task,
                advance=10,
                description=f"[green]Checking for existing active snapshot named {snapshot_name}",
            )
            self.query_existing_active_snapshot(snapshot_name)

            # Step 2: Wait for snapshot to complete (60% progress)
            progress.update(task, description="[green]Waiting for snapshot to complete")
            snapshot = self.poll_for_completion(snapshot_id, progress, task)

            # Step 3: Finalize snapshot (30% progress)
            progress.update(task, advance=30, description="[green]Finalizing snapshot")
            self.delete_snapshot()
            self.rename_snapshot(snapshot_id, snapshot_name)
            return snapshot


class BaseDevhubTask(BaseSalesforceTask):
    """Base class for tasks that need DevHub access."""

    def _init_task(self):
        super()._init_task()
        self.devhub = self._get_devhub_api()

    def _get_devhub_api(self, base_url=None):
        self.logger.info("Getting Dev Hub access token")
        p = sfdx("config get target-dev-hub --json")
        try:
            devhub_username = json.loads(p.stdout_text.read())["result"][0]["value"]
        except (json.JSONDecodeError, KeyError):
            raise SnapshotError(
                f"Failed to get Dev Hub username from sfdx: {p.stdout_text.read()}"
            )

        p = sfdx(
            f"force:org:display --json",
            username=devhub_username,
            log_note="Getting Dev Hub org info",
        )
        try:
            devhub_info = json.loads(p.stdout_text.read())["result"]
        except (json.JSONDecodeError, KeyError):
            raise SnapshotError(
                f"Failed to get Dev Hub information from sfdx: {p.stdout_text.read()}"
            )

        devhub = DevHubOrgConfig(
            access_token=devhub_info["accessToken"],
            instance_url=devhub_info["instanceUrl"],
        )
        return get_simple_salesforce_connection(
            project_config=self.project_config,
            org_config=devhub,
            api_version=self.api_version,
            base_url=base_url,
        )


class SnapshotError(CumulusCIException):
    pass


class DevHubOrgConfig(BaseModel):
    access_token: str = Field(..., description="Access token for the Dev Hub org")
    instance_url: str = Field(..., description="Instance URL for the Dev Hub org")


class BaseDevhubTask(BaseSalesforceTask):
    """Base class for tasks that need DevHub access."""

    def _init_task(self):
        """Initialize the task and authenticate to DevHub."""
        super()._init_task()
        self.devhub = self._get_devhub_api()

    def _get_devhub_api(self, base_url=None):
        self.logger.info("Getting Dev Hub access token")
        p = sfdx(
            "config get target-dev-hub --json",
        )
        try:
            result = p.stdout_text.read()
            data = json.loads(result)
            devhub_username = data["result"][0]["value"]
        except json.JSONDecodeError:
            raise SnapshotError(f"Failed to parse SFDX output: {p.stdout_text.read()}")
        except KeyError:
            raise SnapshotError(
                f"Failed to get Dev Hub username from sfdx. Please use `sfdx force:config:set target-dev-hub=<username>` to set the target Dev Hub org."
            )

        p = sfdx(
            f"force:org:display --json",
            username=devhub_username,
            log_note="Getting Dev Hub org info",
        )

        try:
            devhub_info = json.loads(p.stdout_text.read())
        except json.JSONDecodeError:
            raise SnapshotError(f"Failed to parse SFDX output: {p.stdout_text.read()}")

        if "result" not in devhub_info:
            raise SnapshotError(
                f"Failed to get Dev Hub information from sfdx: {devhub_info}"
            )
        devhub = DevHubOrgConfig(
            access_token=devhub_info["result"]["accessToken"],
            instance_url=devhub_info["result"]["instanceUrl"],
        )
        return get_simple_salesforce_connection(
            project_config=self.project_config,
            org_config=devhub,
            api_version=self.api_version,
            base_url=base_url,
        )


class CreateScratchOrgSnapshot(BaseSalesforceTask):
    task_docs = """
    Creates a Scratch Org Snapshot using the Dev Hub org.
   
    **Requires** *`target-dev-hub` configured globally or for the project, used as the target Dev Hub org for Scratch Org Snapshots*.
    
    Interacts directly with the OrgSnapshot object in the Salesforce API to fully automate the process of maintaining one active snapshot per snapshot name.
    
    *Snapshot Creation Process*
    
    - **Check for an existing `active` OrgSnapshot** with the same name and recording its ID
    - **Check for an existing `in-progress` OrgSnapshot** with the same name and delete it, maintaining only one in-progress snapshot build
    - **Create a temporary snapshot** under a temporary name with the provided description
    - **Poll for completion** of the snapshot creation process
    
    *On Successful OrgSnapshot Completion*
    
    - Delete the existing snapshot
    - Rename the snapshot to the desired name
    - Report the snapshot details including the ID, status, and expiration date
   

    """

    temp_snapshot_suffix = "0"

    task_options = {
        "snapshot_name": {
            "description": "Name of the snapshot to create",
            "required": True,
        },
        "description": {
            "description": "Description of the snapshot",
            "required": False,
        },
    }
    # Peg to API Version 60.0 for OrgSnapshot object
    api_version = "60.0"
    salesforce_task = True

    def __init__(self, *args, **kwargs):
        self.current_snapshot_id = None
        self.temp_snapshot_name = None
        self.sf = None
        self.snapshot_id = None
        self.start_time = None
        super().__init__(*args, **kwargs)

    def _init_task(self):
        self.sf = self._get_devhub_api()

    def _init_options(self, kwargs):
        super()._init_options(kwargs)
        max_length = 15 - len(self.temp_snapshot_suffix)
        if len(self.options["snapshot_name"]) > max_length:
            raise SnapshotError(
                f"Snapshot name must be {max_length} characters or less"
            )
        self.temp_snapshot_name = (
            f"{self.options['snapshot_name']}{self.temp_snapshot_suffix}"
        )
        self.console = Console()

    def _run_task(self):
        self.logger.info("Starting scratch org snapshot creation")
        self._check_existing_snapshot()
        self._create_snapshot()
        self._poll()
        self._rename_snapshot()
        self._report_result()

    def _get_devhub_api(self, base_url=None):
        self.logger.info("Getting Dev Hub access token")
        p = sfdx(
            "config get target-dev-hub --json",
        )
        try:
            devhub_username = json.loads(p.stdout_text.read())["result"][0]["value"]
        except json.JSONDecodeError:
            raise SnapshotError(f"Failed to parse SFDX output: {p.stdout_text.read()}")
        except KeyError:
            raise SnapshotError(
                f"Failed to get Dev Hub username from sfdx: {p.stdout_text.read()}"
            )

        p = sfdx(
            f"force:org:display --json",
            username=devhub_username,
            log_note="Getting Dev Hub org info",
        )

        try:
            devhub_info = json.loads(p.stdout_text.read())
        except json.JSONDecodeError:
            raise SnapshotError(f"Failed to parse SFDX output: {p.stdout_text.read()}")

        if "result" not in devhub_info:
            raise SnapshotError(
                f"Failed to get Dev Hub information from sfdx: {devhub_info}"
            )
        devhub = DevHubOrgConfig(
            access_token=devhub_info["result"]["accessToken"],
            instance_url=devhub_info["result"]["instanceUrl"],
        )
        return get_simple_salesforce_connection(
            project_config=self.project_config,
            org_config=devhub,
            api_version=self.api_version,
            base_url=base_url,
        )

    def _check_existing_snapshot(self):
        query = f"SELECT Id, Status FROM OrgSnapshot WHERE SnapshotName = '{self.options['snapshot_name']}'"
        result = self.sf.query(query)
        if result["totalSize"] > 0:
            snapshot = result["records"][0]
            if snapshot["Status"] == "In Progress":
                raise SnapshotError(
                    f"Snapshot '{self.options['snapshot_name']}' is already being created."
                )
            else:
                self.current_snapshot_id = snapshot["Id"]
                self.logger.info(
                    f"Found existing snapshot '{self.options['snapshot_name']}' with id {self.current_snapshot_id}"
                )
        query = f"SELECT Id FROM OrgSnapshot WHERE SnapshotName = '{self.temp_snapshot_name}'"
        result = self.sf.query(query)
        if result["totalSize"] > 0:
            snapshot = result["records"][0]
            self.logger.info(
                f"Deleting in-progress snapshot '{self.temp_snapshot_name}'"
            )
            self.sf.OrgSnapshot.delete(snapshot["Id"])

    def _create_snapshot(self):
        self.logger.info(
            f"Creating snapshot: {self.options['snapshot_name']} as {self.temp_snapshot_name}"
        )
        try:

            snapshot = self.sf.OrgSnapshot.create(
                {
                    "SnapshotName": self.temp_snapshot_name,
                    "Description": self.options["description"],
                    "SourceOrg": self.org_config.org_id,
                    "Content": "metadatadata",
                }
            )
            self.snapshot_id = snapshot["id"]
            self.start_time = time.time()
        except SalesforceException as e:
            if "NOT_FOUND" in str(e):
                raise SnapshotError(
                    "Org snapshot feature is not enabled for this Dev Hub."
                ) from e
            raise

    def _rename_snapshot(self):
        if self.current_snapshot_id:
            self.logger.info(
                f"Deleting existing snapshot '{self.options['snapshot_name']}'"
            )
            self.sf.OrgSnapshot.delete(self.current_snapshot_id)
        self.logger.info(f"Renaming snapshot to '{self.options['snapshot_name']}'")
        self.sf.OrgSnapshot.update(
            self.snapshot_id, {"SnapshotName": self.options["snapshot_name"]}
        )
        self.logger.info(f"Snapshot renamed to '{self.options['snapshot_name']}'")

    def _poll_action(self):
        try:
            snapshot = self.sf.OrgSnapshot.get(self.snapshot_id)
        except SalesforceResourceNotFound as exc:
            raise SnapshotError(
                "Snapshot not found. This usually happens because another build deleted the while it was being built snapshot."
            ) from exc
        status = snapshot["Status"]
        self.logger.info(f"Snapshot status: {status}")
        if status == "Active":
            self.poll_complete = True
        elif status == "Error":
            raise SnapshotError(
                f"Snapshot creation failed: {snapshot.get('Error', 'Unknown error')}"
            )

    def _poll_update_interval(self):
        super()._poll_update_interval()
        if self.poll_interval_s > 30:
            self.poll_interval_s = 30

    def _report_result(self):
        result = self.sf.query(
            f"SELECT {','.join(ORG_SNAPSHOT_FIELDS)} FROM OrgSnapshot WHERE Id = '{self.snapshot_id}'"
        )
        snapshot = result["records"][0]
        self._print_snapshot_details(snapshot)

        end_time = time.time()
        duration = end_time - self.start_time
        duration_minutes = int(duration // 60)
        duration_seconds = int(duration % 60)
        duration_str = f"{duration_minutes}m and {duration_seconds}s"
        self.logger.info(f"Snapshot created in {duration_str}")

        # Output to GitHub Actions Job Summary
        summary_file = os.getenv("GITHUB_STEP_SUMMARY")
        if summary_file:
            with open(summary_file, "a") as f:
                f.write(f"## Snapshot Creation Summary\n")
                f.write(f"- **Duration**: {duration_str}\n")
                f.write(f"- **Snapshot ID**: {self.snapshot_id}\n")
                f.write(f"- **Fields**: {', '.join(ORG_SNAPSHOT_FIELDS)}\n")
                f.write("\n### Snapshot Details\n")
                for field in ORG_SNAPSHOT_FIELDS:
                    if field in snapshot:
                        value = snapshot[field]
                        if field in ["CreatedDate", "LastModifiedDate"]:
                            value = self._format_datetime(value)
                        elif field == "ExpirationDate":
                            value = self._format_date(value)
                        f.write(f"- **{field}**: {value}\n")

    def _print_snapshot_details(self, snapshot):
        table = Table(title="Snapshot Details")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="magenta")

        for field in ORG_SNAPSHOT_FIELDS:
            if field in snapshot:
                value = snapshot[field]
                if field in ["CreatedDate", "LastModifiedDate"]:
                    value = self._format_datetime(value)
                elif field == "ExpirationDate":
                    value = self._format_date(value)
                table.add_row(field, str(value))

        self.console.print(table)

    def _format_datetime(self, date_string):
        if date_string is None:
            return "N/A"
        dt = parse(date_string)
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    def _format_date(self, date_string):
        if date_string is None:
            return "N/A"
        return datetime.strptime(date_string, "%Y-%m-%d").strftime("%Y-%m-%d")


class GithubPullRequestSnapshot(BaseGithubTask, BaseDevhubTask):
    task_docs = """
    Creates a Scratch Org Snapshot for a GitHub Pull Request based on build status and conditions.
    """

    task_options = {
        "wait": {
            "description": "Whether to wait for the snapshot creation to complete. Defaults to True. If False, the task will return immediately after creating the snapshot. Use for running in a split workflow on GitHub. Looks for the GITHUB_OUTPUT environment variable and outputs SNAPSHOT_ID=<id> to it if found for use in later steps.",
        },
        "snapshot_id": {
            "description": "The ID of the in-progress snapshot to wait for completion. If set, the task will wait for the snapshot to complete and update the existing snapshot with the new details. Use for the second step of a split workflow on GitHub.",
        },
        "project_code": {"description": "Two-character project code", "required": True},
        "base_branch": {
            "description": "Base branch for the pull request. Defaults to the default branch",
            "required": False,
        },
        "build_success": {
            "description": "Set to True if the build was successful or False for a failure. Defaults to True.",
            "required": True,
        },
        "build_fail_tests": {
            "description": "Whether the build failed due to test failures. Defaults to False",
            "required": True,
        },
        "commit_status_context": {
            "description": "The context for the commit status check containing the snapshot name. If unset, no commit status is created.",
            "required": False,
        },
        "snapshot_is_packaged": {
            "description": "Set to True if the snapshot is for a packaged build or False for unpackaged build",
            "required": True,
        },
        "snapshot_pr": {
            "description": "Whether to create a snapshot for feature branches with PRs",
            "required": False,
        },
        "snapshot_pr_label": {
            "description": "Limit snapshot creation to only PRs with this label",
            "required": False,
        },
        "snapshot_pr_draft": {
            "description": "Whether to create snapshots for draft PRs",
            "required": False,
        },
        "snapshot_fail_pr": {
            "description": "Whether to create snapshots for failed builds on branches with an open PR",
            "required": False,
        },
        "snapshot_fail_pr_label": {
            "description": "Limit failure snapshot creation to only PRs with this label",
            "required": False,
        },
        "snapshot_fail_pr_draft": {
            "description": "Whether to create snapshots for failed draft PR builds",
            "required": False,
        },
        "snapshot_fail_test_only": {
            "description": "Whether to create snapshots only for test failures",
            "required": False,
        },
        "github_environment_prefix": {
            "description": "If set, a GitHub Environment will be created for active snapshots using this prefix in the Environment name. If unset, no environment is created.",
            "required": False,
        },
    }
    api_version = "60.0"
    salesforce_task = True

    def _init_options(self, kwargs):
        super()._init_options(kwargs)
        self.options["build_success"] = process_bool_arg(
            self.options.get("build_success", True)
        )
        self.options["build_fail_tests"] = process_bool_arg(
            self.options.get("build_fail_tests")
        )
        self.options["commit_status_context"] = self.options.get(
            "commit_status_context"
        )
        self.options["wait"] = process_bool_arg(self.options.get("wait", True))
        self.options["snapshot_id"] = self.options.get("snapshot_id")
        self.options["snapshot_is_packaged"] = process_bool_arg(
            self.options.get("snapshot_is_packaged")
        )
        self.options["snapshot_pr"] = process_bool_arg(
            self.options.get("snapshot_pr", True)
        )
        self.options["snapshot_pr_draft"] = process_bool_arg(
            self.options.get("snapshot_pr_draft", False)
        )
        self.options["snapshot_fail_pr"] = process_bool_arg(
            self.options.get("snapshot_fail_pr", True)
        )
        self.options["snapshot_fail_pr_draft"] = process_bool_arg(
            self.options.get("snapshot_fail_pr_draft", False)
        )
        self.options["snapshot_fail_test_only"] = process_bool_arg(
            self.options.get("snapshot_fail_test_only", False)
        )
        self.options["snapshot_pr_label"] = self.options.get("snapshot_pr_label")
        self.options["snapshot_fail_pr_label"] = self.options.get(
            "snapshot_fail_pr_label"
        )
        self.options["base_branch"] = self.options.get(
            "base_branch", self.project_config.project__git__default_branch
        )
        self.options["github_environment_prefix"] = self.options.get(
            "github_environment_prefix"
        )

        self.console = Console()

    def _init_task(self):
        super()._init_task()
        self.repo = self.get_repo()

    def _run_task(self):
        pr = self._get_pull_request()

        if self._should_create_snapshot(pr):
            snapshot_name = self._generate_snapshot_name(pr)
            description = self._generate_snapshot_description(pr)

            snapshot_manager = SnapshotManager(self.devhub, self.logger)
            try:
                if self.options["snapshot_id"]:
                    snapshot = snapshot_manager.finalize_temp_snapshot(
                        snapshot_name=snapshot_name,
                        description=description,
                        snapshot_id=self.options["snapshot_id"],
                    )
                else:
                    snapshot = snapshot_manager.update_snapshot_from_org(
                        base_name=snapshot_name,
                        description=description,
                        source_org=self.org_config.org_id,
                        wait=self.options["wait"],
                    )
            except SnapshotError as e:
                self.console.print(
                    Panel(
                        f"Failed to create snapshot: {str(e)}",
                        title="Snapshot Creation",
                        border_style="red",
                    )
                )
                if self.options["commit_status_context"]:
                    self._create_commit_status(snapshot_name, "error")
                raise

            self.return_values["snapshot_id"] = snapshot.get("Id")
            self.return_values["snapshot_name"] = snapshot.get("SnapshotName")
            self.return_values["snapshot_description"] = snapshot.get("Description")
            self.return_values["snapshot_status"] = snapshot.get("Status")

            self._report_result(snapshot)
            if self.options["wait"] is False:
                if os.getenv("GITHUB_OUTPUT"):
                    with open(os.getenv("GITHUB_OUTPUT"), "w") as f:
                        f.write(f"SNAPSHOT_ID={snapshot['Id']}")
                        return True

            if self.options["commit_status_context"]:
                active = self.return_values["snapshot_status"] == "Active"
                self._create_commit_status(
                    snapshot_name=(
                        snapshot_name
                        if active
                        else f"{snapshot_name} ({self.return_values['snapshot_status']})"
                    ),
                    state="success" if active else "error",
                )
            if self.options["github_environment_prefix"]:
                self._create_github_environment(snapshot_name)

        else:
            if self.options.get("snapshot_id"):
                self.logger.warning(
                    "In-progress snapshot does not meet conditions for finalization. Deleting..."
                )

            self.console.print(
                Panel(
                    f"No snapshot creation required based on current conditions. {self.return_values.get('skip_reason','')}",
                    title="Snapshot Creation",
                    border_style="yellow",
                )
            )

    def _get_pull_request(self):
        res = self.repo.pull_requests()
        for pr in res:
            # For some reason, github3.py or the GitHub API is returning non-matching PRs
            # This is a workaround to ensure we get the correct PR
            self.logger.info(
                f"Checking PR: {pr.number} [{pr.state}] {pr.head.ref} -> {pr.base.ref}"
            )
            if (
                pr.state == "open"
                and pr.head.ref == self.project_config.repo_branch
                and pr.base.ref == self.options["base_branch"]
            ):
                return pr

    def _should_create_snapshot(self, pr):
        is_pr = pr is not None
        self.return_values["has_pr"] = is_pr
        is_draft = pr.draft if is_pr else False
        self.return_values["pr_is_draft"] = is_draft
        pr_labels = [label["name"] for label in pr.labels] if is_pr else []
        has_snapshot_label = self.options["snapshot_pr_label"] in pr_labels
        has_snapshot_fail_label = self.options["snapshot_fail_pr_label"] in pr_labels
        self.return_values["pr_has_snapshot_label"] = has_snapshot_label
        self.return_values["pr_has_snapshot_fail_label"] = has_snapshot_fail_label

        if self.options["build_success"] is True:
            if not self.options["snapshot_pr"]:
                self.return_values["skip_reason"] = "snapshot_pr is False"
                return False
            elif not is_pr:
                self.return_values["skip_reason"] = "No pull request on the branch"
                return False
            elif self.options["snapshot_pr_label"] and not has_snapshot_label:
                self.return_values["skip_reason"] = (
                    "Pull request does not have snapshot label"
                )
                return False
            elif is_draft and not self.options["snapshot_pr_draft"]:
                self.return_values["skip_reason"] = (
                    "Pull request is draft and snapshot_pr_draft is False"
                )
                return False
            return True
        else:
            if is_pr:
                return (
                    self.options["snapshot_fail_pr"]
                    and (not is_draft or self.options["snapshot_fail_pr_draft"])
                    and (
                        not self.options["snapshot_fail_pr_label"]
                        or has_snapshot_fail_label
                    )
                    and (
                        not self.options["snapshot_fail_test_only"]
                        or not self.options["build_fail_tests"]
                    )
                )
            else:
                return True

    def _generate_snapshot_name(self, pr):
        project_code = self.options["project_code"]
        pr_number = pr.number if pr else "NoPR"

        if self.options["build_success"] is True:
            return f"{project_code}Pr{pr_number}M"
        else:
            if self.options["snapshot_fail_test_only"]:
                return f"{project_code}FTest{pr_number}M"
            else:
                return f"{project_code}Fail{pr_number}M"

    def _generate_snapshot_description(self, pr):
        if self.options["build_success"] is True:
            return f"Snapshot for PR #{pr.number}: {pr.title} of branch {self.project_config.repo_branch} for commit {self.project_config.repo_commit}"
        else:
            return f"Snapshot for failed build on PR #{pr.number}: {pr.title} of branch {self.project_config.repo_branch} for commit {self.project_config.repo_commit}"

    def _report_result(self, snapshot):
        table = Table(title="Snapshot Details", border_style="cyan")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="magenta")

        for field in [
            "Id",
            "SnapshotName",
            "Status",
            "Description",
            "CreatedDate",
            "ExpirationDate",
        ]:
            value = snapshot.get(field, "N/A")
            if field in ["CreatedDate", "ExpirationDate"]:
                value = self._format_datetime(value)
            table.add_row(field, str(value))

        self.console.print(table)

        # Output to GitHub Actions Job Summary
        summary_file = os.getenv("GITHUB_STEP_SUMMARY")
        if summary_file:
            with open(summary_file, "a") as f:
                f.write(f"## Snapshot Creation Summary\n")
                f.write(f"- **Snapshot ID**: {snapshot.get('Id')}\n")
                f.write(f"- **Snapshot Name**: {snapshot.get('SnapshotName')}\n")
                f.write(f"- **Status**: {snapshot.get('Status')}\n")
                f.write(f"- **Description**: {snapshot.get('Description')}\n")
                f.write(
                    f"- **Created Date**: {self._format_datetime(snapshot.get('CreatedDate'))}\n"
                )
                f.write(
                    f"- **Expiration Date**: {self._format_datetime(snapshot.get('ExpirationDate'))}\n"
                )

    def _format_datetime(self, date_string):
        if date_string is None:
            return "N/A"
        dt = parse(date_string)
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    def _create_commit_status(self, snapshot_name, state):
        try:
            description = f"Snapshot: {snapshot_name}"
            self.repo.create_status(
                self.project_config.repo_commit,
                state,
                target_url=os.environ.get("JOB_URL"),
                description=description,
                context=self.options["commit_status_context"],
            )
        except GitHubError as e:
            self.logger.error(f"Failed to create commit status: {str(e)}")
            self.console.print(
                Panel(
                    f"Failed to create commit status: {str(e)}",
                    title="Commit Status",
                    border_style="red",
                )
            )

    def _create_github_environment(self, snapshot_name):
        try:
            environment_name = (
                f"{self.options['github_environment_prefix']}{snapshot_name}"
            )

            # Check if environment already exists
            resp = self.repo._get(f"{self.repo.url}/environments/{environment_name}")
            if resp.status_code == 404:
                self.logger.info(f"Creating new environment: {environment_name}")
                resp = self.repo._put(
                    f"{self.repo.url}/environments/{environment_name}",
                )
                resp.raise_for_status()
                self.logger.info(f"Created new environment: {environment_name}")
            else:
                self.logger.info(f"Environment '{environment_name}' already exists.")

            environment = resp.json()

            self.console.print(
                Panel(
                    f"GitHub Environment '{environment_name}' created/updated successfully!",
                    title="Environment Creation",
                    border_style="green",
                )
            )

        except Exception as e:
            self.logger.error(f"Failed to create/update GitHub Environment: {str(e)}")
            self.console.print(
                Panel(
                    f"Failed to create/update GitHub Environment: {str(e)}",
                    title="Environment Creation",
                    border_style="red",
                )
            )
            raise
