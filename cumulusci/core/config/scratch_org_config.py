import datetime
import json
import os
from typing import List, NoReturn, Optional

import sarge

from cumulusci.core.config import FAILED_TO_CREATE_SCRATCH_ORG
from cumulusci.core.config.sfdx_org_config import SfdxOrgConfig
from cumulusci.core.exceptions import (
    CumulusCIException,
    ScratchOrgException,
    ServiceNotConfigured,
)
from cumulusci.core.sfdx import sfdx


class ScratchOrgConfig(SfdxOrgConfig):
    """Salesforce DX Scratch org configuration"""

    noancestors: bool
    # default = None  # what is this?
    instance: str
    password_failed: bool
    devhub: str
    release: str

    createable: bool = True

    @property
    def scratch_info(self):
        """Deprecated alias for sfdx_info.

        Will create the scratch org if necessary.
        """
        return self.sfdx_info

    @property
    def days(self) -> int:
        return self.config.setdefault("days", 1)

    @property
    def active(self) -> bool:
        """Check if an org is alive"""
        return self.date_created and not self.expired

    @property
    def expired(self) -> bool:
        """Check if an org has already expired"""
        now = datetime.datetime.now(datetime.timezone.utc)
        if self.expires and self.expires.tzinfo is None:
            # Convert naive expires to UTC for comparison
            now = now.replace(tzinfo=None)
        return bool(self.expires) and self.expires < now

    @property
    def expires(self) -> Optional[datetime.datetime]:
        if self.date_created:
            return self.date_created + datetime.timedelta(days=int(self.days))

    @property
    def days_alive(self) -> Optional[int]:
        if self.date_created and not self.expired:
            if self.date_created.tzinfo is None:
                # For naive date_created, use naive local time for consistent comparison
                now = datetime.datetime.now()
            else:
                # For timezone-aware date_created, use timezone-aware UTC time
                now = datetime.datetime.now(datetime.timezone.utc)
            delta = now - self.date_created
            return delta.days + 1

    def create_org(self) -> None:
        """Uses sf org create scratch  to create the org"""
        if not self.config_file:
            raise ScratchOrgException(
                f"Scratch org config {self.name} is missing a config_file"
            )
        if not self.scratch_org_type:
            self.config["scratch_org_type"] = "workspace"

        args: List[str] = self._build_org_create_args()
        extra_args = os.environ.get("SFDX_ORG_CREATE_ARGS", "")
        p: sarge.Command = sfdx(
            f"org create scratch --json {extra_args}",
            args=args,
            username=None,
            log_note="Creating scratch org",
        )
        stdout = p.stdout_text.read()
        stderr = p.stderr_text.read()

        def raise_error() -> NoReturn:
            message = f"{FAILED_TO_CREATE_SCRATCH_ORG}: \n{stdout}\n{stderr}"
            try:
                output = json.loads(stdout)
                if (
                    output.get("message") == "The requested resource does not exist"
                    and output.get("name") == "NOT_FOUND"
                ):
                    raise ScratchOrgException(
                        "The Salesforce CLI was unable to create a scratch org. Ensure you are connected using a valid API version on an active Dev Hub."
                    )
            except json.decoder.JSONDecodeError:
                raise ScratchOrgException(message)

            raise ScratchOrgException(message)

        result = {}  # for type checker.
        if p.returncode:
            raise_error()
        try:
            result = json.loads(stdout)

        except json.decoder.JSONDecodeError:
            raise_error()

        if (
            not (res := result.get("result"))
            or ("username" not in res)
            or ("orgId" not in res)
        ):
            raise_error()

        if res["username"] is None:
            raise ScratchOrgException(
                "SFDX claimed to be successful but there was no username "
                "in the output...maybe there was a gack?"
            )

        self.config["org_id"] = res["orgId"]
        self.config["username"] = res["username"]

        self.config["date_created"] = datetime.datetime.now(datetime.timezone.utc)

        self.logger.error(stderr)

        self.logger.info(
            f"Created: OrgId: {self.config['org_id']}, Username:{self.config['username']}"
        )

        if self.config.get("set_password"):
            self.generate_password()

        # Flag that this org has been created
        self.config["created"] = True

    def _build_org_create_args(self) -> List[str]:
        args = ["-f", self.config_file, "-w", "120"]
        devhub_username: Optional[str] = self._choose_devhub_username()
        if devhub_username:
            args += ["--target-dev-hub", devhub_username]
        if not self.namespaced:
            args += ["--no-namespace"]
        if self.noancestors:
            args += ["--no-ancestors"]
        if self.days:
            args += ["--duration-days", str(self.days)]
        if self.release:
            args += [f"--release={self.release}"]
        if self.sfdx_alias:
            args += ["-a", self.sfdx_alias]
        with open(self.config_file, "r") as org_def:
            org_def_data = json.load(org_def)
            org_def_has_email = "adminEmail" in org_def_data
        if self.email_address and not org_def_has_email:
            args += [f"--admin-email={self.email_address}"]
        if self.default:
            args += ["--set-default"]

        return args

    def _choose_devhub_username(self) -> Optional[str]:
        """Determine which devhub username to specify when calling sfdx, if any."""
        # If a devhub was specified via `cci org scratch`, use it.
        # (This will return None if "devhub" isn't set in the org config,
        # in which case sf will use its target-dev-hub.)
        devhub_username = self.devhub
        if not devhub_username and self.keychain is not None:
            # Otherwise see if one is configured via the "devhub" service
            try:
                devhub_service = self.keychain.get_service("devhub")
            except (ServiceNotConfigured, CumulusCIException):
                pass
            else:
                devhub_username = devhub_service.username
        return devhub_username

    def generate_password(self) -> None:
        """Generates an org password with: sf org generate password.
        On a non-zero return code, set the password_failed in our config
        and log the output (stdout/stderr) from sfdx."""

        if self.password_failed:
            self.logger.warning("Skipping resetting password since last attempt failed")
            return

        p: sarge.Command = sfdx(
            "org generate password",
            self.username,
            log_note="Generating scratch org user password",
        )

        if p.returncode:
            self.config["password_failed"] = True
            stderr = p.stderr_text.readlines()
            stdout = p.stdout_text.readlines()
            # Don't throw an exception because of failure creating the
            # password, just notify in a log message
            nl = "\n"  # fstrings can't contain backslashes
            self.logger.warning(
                f"Failed to set password: \n{nl.join(stdout)}\n{nl.join(stderr)}"
            )

    def format_org_days(self) -> str:
        if self.days_alive:
            org_days = f"{self.days_alive}/{self.days}"
        else:
            org_days = str(self.days)
        return org_days

    def can_delete(self) -> bool:
        return bool(self.date_created)

    def delete_org(self) -> None:
        """Uses sf org delete scratch to delete the org"""
        if not self.created:
            self.logger.info("Skipping org deletion: the scratch org does not exist.")
            return

        p: sarge.Command = sfdx(
            "org delete scratch -p", self.username, "Deleting scratch org"
        )
        sfdx_output: List[str] = list(p.stdout_text) + list(p.stderr_text)

        for line in sfdx_output:
            if "error" in line.lower():
                self.logger.error(line)
            else:
                self.logger.info(line)

        if p.returncode:
            message = "Failed to delete scratch org"
            raise ScratchOrgException(message)

        # Flag that this org has been deleted
        self.config["created"] = False
        self.config["username"] = None
        self.config["date_created"] = None
        self.config["instance_url"] = None
        self.save()
