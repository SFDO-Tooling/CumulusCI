import datetime
import json
import os

from cumulusci.core.config import FAILED_TO_CREATE_SCRATCH_ORG
from cumulusci.core.config.sfdx_org_config import SfdxOrgConfig
from cumulusci.core.exceptions import (
    CumulusCIException,
    ScratchOrgException,
    ServiceNotConfigured,
)
from cumulusci.core.sfdx import sfdx

nl = "\n"  # fstrings can't contain backslashes


class ScratchOrgConfig(SfdxOrgConfig):
    """Salesforce DX Scratch org configuration"""

    noancestors: bool
    # default = None  # what is this?
    instance: str
    password_failed: bool
    devhub: str

    createable: bool = True

    @property
    def scratch_info(self):
        """Deprecated alias for sfdx_info.

        Will create the scratch org if necessary.
        """
        return self.sfdx_info

    @property
    def days(self):
        return self.config.setdefault("days", 1)

    @property
    def active(self):
        """Check if an org is alive"""
        return self.date_created and not self.expired

    @property
    def expired(self):
        """Check if an org has already expired"""
        return bool(self.expires) and self.expires < datetime.datetime.utcnow()

    @property
    def expires(self):
        if self.date_created:
            return self.date_created + datetime.timedelta(days=int(self.days))

    @property
    def days_alive(self):
        if self.date_created and not self.expired:
            delta = datetime.datetime.utcnow() - self.date_created
            return delta.days + 1

    def create_org(self):
        """Uses sfdx force:org:create to create the org"""
        if not self.config_file:
            raise ScratchOrgException(
                f"Scratch org config {self.name} is missing a config_file"
            )
        if not self.scratch_org_type:
            self.config["scratch_org_type"] = "workspace"

        args = self._build_org_create_args()
        extra_args = os.environ.get("SFDX_ORG_CREATE_ARGS", "")
        p = sfdx(
            f"force:org:create --json {extra_args}",
            args=args,
            username=None,
            log_note="Creating scratch org",
        )
        stdout = p.stdout_text.read()
        stderr = p.stderr_text.read()

        def raise_error():
            message = f"{FAILED_TO_CREATE_SCRATCH_ORG}: \n{stdout}\n{stderr}"
            raise ScratchOrgException(message)

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

        self.config["date_created"] = datetime.datetime.utcnow()

        self.logger.error(stderr)

        self.logger.info(
            f"Created: OrgId: {self.config['org_id']}, Username:{self.config['username']}"
        )

        if self.config.get("set_password"):
            self.generate_password()

        # Flag that this org has been created
        self.config["created"] = True

    def _build_org_create_args(self):
        args = ["-f", self.config_file, "-w", "120"]
        devhub = self._choose_devhub()
        if devhub:
            args += ["--targetdevhubusername", devhub]
        if not self.namespaced:
            args += ["-n"]
        if self.noancestors:
            args += ["--noancestors"]
        if self.days:
            args += ["--durationdays", str(self.days)]
        if self.sfdx_alias:
            args += ["-a", self.sfdx_alias]
        with open(self.config_file, "r") as org_def:
            org_def_data = json.load(org_def)
            org_def_has_email = "adminEmail" in org_def_data
        if self.email_address and not org_def_has_email:
            args += [f"adminEmail={self.email_address}"]
        if self.default:
            args += ["-s"]
        instance = self.instance or os.environ.get("SFDX_SIGNUP_INSTANCE")
        if instance:
            args += [f"instance={instance}"]
        return args

    def _choose_devhub(self):
        """Determine which devhub to specify when calling sfdx, if any."""
        # If a devhub was specified via `cci org scratch`, use it.
        # (This will return None if "devhub" isn't set in the org config,
        # in which case sfdx will use its defaultdevhubusername.)
        devhub = self.devhub
        if not devhub and self.keychain is not None:
            # Otherwise see if one is configured via the "devhub" service
            try:
                devhub_service = self.keychain.get_service("devhub")
            except (ServiceNotConfigured, CumulusCIException):
                pass
            else:
                devhub = devhub_service.username
        return devhub

    def generate_password(self):
        """Generates an org password with the sfdx utility."""

        if self.password_failed:
            self.logger.warning("Skipping resetting password since last attempt failed")
            return

        # Set a random password so it's available via cci org info

        p = sfdx(
            "force:user:password:generate",
            self.username,
            log_note="Generating scratch org user password",
        )

        stderr = p.stderr_text.readlines()
        stdout = p.stdout_text.readlines()

        if p.returncode:
            self.config["password_failed"] = True
            # Don't throw an exception because of failure creating the
            # password, just notify in a log message
            self.logger.warning(
                f"Failed to set password: \n{nl.join(stdout)}\n{nl.join(stderr)}"
            )

    def format_org_days(self):
        if self.days_alive:
            org_days = f"{self.days_alive}/{self.days}"
        else:
            org_days = str(self.days)
        return org_days

    def can_delete(self):
        return bool(self.date_created)

    def delete_org(self):
        """Uses sfdx force:org:delete to delete the org"""
        if not self.created:
            self.logger.info(
                "Skipping org deletion: the scratch org has not been created"
            )
            return

        p = sfdx("force:org:delete -p", self.username, "Deleting scratch org")

        output = []
        for line in list(p.stdout_text) + list(p.stderr_text):
            output.append(line)
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
