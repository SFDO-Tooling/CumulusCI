import datetime
import json
import os
import re

import sarge

from cumulusci.utils import get_git_config
from cumulusci.core.sfdx import sfdx
from cumulusci.core.config import FAILED_TO_CREATE_SCRATCH_ORG
from cumulusci.core.config import OrgConfig
from cumulusci.core.exceptions import ScratchOrgException
from cumulusci.core.exceptions import ServiceNotConfigured

nl = "\n"  # fstrings can't contain backslashes


class ScratchOrgConfig(OrgConfig):
    """ Salesforce DX Scratch org configuration """

    @property
    def scratch_info(self):
        if hasattr(self, "_scratch_info"):
            return self._scratch_info

        # Create the org if it hasn't already been created
        if not self.created:
            self.create_org()

        self.logger.info("Getting scratch org info from Salesforce DX")

        username = self.config.get("username")
        if not username:
            raise ScratchOrgException(
                "SFDX claimed to be successful but there was no username "
                "in the output...maybe there was a gack?"
            )

        # Call force:org:display and parse output to get instance_url and
        # access_token
        p = sfdx("force:org:display --json", self.username)

        org_info = None
        stderr_list = [line.strip() for line in p.stderr_text]
        stdout_list = [line.strip() for line in p.stdout_text]

        if p.returncode:
            self.logger.error(f"Return code: {p.returncode}")
            for line in stderr_list:
                self.logger.error(line)
            for line in stdout_list:
                self.logger.error(line)
            message = f"\nstderr:\n{nl.join(stderr_list)}"
            message += f"\nstdout:\n{nl.join(stdout_list)}"
            raise ScratchOrgException(message)

        else:
            try:
                org_info = json.loads("".join(stdout_list))
            except Exception as e:
                raise ScratchOrgException(
                    "Failed to parse json from output. This can happen if "
                    "your scratch org gets deleted.\n  "
                    f"Exception: {e.__class__.__name__}\n  Output: {''.join(stdout_list)}"
                )
            org_id = org_info["result"]["accessToken"].split("!")[0]

        if "password" in org_info["result"] and org_info["result"]["password"]:
            password = org_info["result"]["password"]
        else:
            password = self.config.get("password")

        self._scratch_info = {
            "instance_url": org_info["result"]["instanceUrl"],
            "access_token": org_info["result"]["accessToken"],
            "org_id": org_id,
            "username": org_info["result"]["username"],
            "password": password,
        }
        self.config.update(self._scratch_info)
        self._scratch_info.update(
            {
                "created_date": org_info["result"].get("createdDate"),
                "expiration_date": org_info["result"].get("expirationDate"),
            }
        )

        self._scratch_info_date = datetime.datetime.utcnow()

        return self._scratch_info

    @property
    def access_token(self):
        return self.scratch_info["access_token"]

    @property
    def instance_url(self):
        return self.config.get("instance_url") or self.scratch_info["instance_url"]

    @property
    def org_id(self):
        org_id = self.config.get("org_id")
        if not org_id:
            org_id = self.scratch_info["org_id"]
        return org_id

    @property
    def user_id(self):
        if not self.config.get("user_id"):
            result = self.salesforce_client.query_all(
                f"SELECT Id FROM User WHERE UserName='{self.username}'"
            )
            self.config["user_id"] = result["records"][0]["Id"]
        return self.config["user_id"]

    @property
    def username(self):
        username = self.config.get("username")
        if not username:
            username = self.scratch_info["username"]
        return username

    @property
    def password(self):
        password = self.config.get("password")
        if not password:
            password = self.scratch_info["password"]
        return password

    @property
    def email_address(self):
        email_address = self.config.get("email_address")
        if not email_address:
            email_address = get_git_config("user.email")
            self.config["email_address"] = email_address

        return email_address

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
        """ Uses sfdx force:org:create to create the org """
        if not self.config_file:
            # FIXME: raise exception
            return
        if not self.scratch_org_type:
            self.config["scratch_org_type"] = "workspace"

        # If the scratch org definition itself contains an `adminEmail` entry,
        # we don't want to override it from our own configuration, which may
        # simply come from the user's Git config.

        with open(self.config_file, "r") as org_def:
            org_def_data = json.load(org_def)
            org_def_has_email = "adminEmail" in org_def_data

        devhub = self._choose_devhub()
        options = {
            "config_file": self.config_file,
            "devhub": f" --targetdevhubusername {devhub}" if devhub else "",
            "namespaced": " -n" if not self.namespaced else "",
            "days": f" --durationdays {self.days}" if self.days else "",
            "wait": " -w 120",
            "alias": sarge.shell_format(' -a "{0!s}"', self.sfdx_alias)
            if self.sfdx_alias
            else "",
            "email": sarge.shell_format('adminEmail="{0!s}"', self.email_address)
            if self.email_address and not org_def_has_email
            else "",
            "default": " -s" if self.default else "",
            "extraargs": os.environ.get("SFDX_ORG_CREATE_ARGS", ""),
        }

        # This feels a little dirty, but the use cases for extra args would mostly
        # work best with env vars
        command = "force:org:create -f {config_file}{devhub}{namespaced}{days}{alias}{default}{wait} {email} {extraargs}".format(
            **options
        )
        p = sfdx(command, username=None, log_note="Creating scratch org")

        stderr = [line.strip() for line in p.stderr_text]
        stdout = [line.strip() for line in p.stdout_text]

        if p.returncode:
            message = f"{FAILED_TO_CREATE_SCRATCH_ORG}: \n{nl.join(stdout)}\n{nl.join(stderr)}"
            raise ScratchOrgException(message)

        re_obj = re.compile("Successfully created scratch org: (.+), username: (.+)")
        for line in stdout:
            match = re_obj.search(line)
            if match:
                self.config["org_id"] = match.group(1)
                self.config["username"] = match.group(2)
            self.logger.info(line)
        for line in stderr:
            self.logger.error(line)

        self.config["date_created"] = datetime.datetime.utcnow()

        if self.config.get("set_password"):
            self.generate_password()

        # Flag that this org has been created
        self.config["created"] = True

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
            except ServiceNotConfigured:
                pass
            else:
                devhub = devhub_service.username
        return devhub

    def generate_password(self):
        """Generates an org password with the sfdx utility. """

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
        """ Uses sfdx force:org:delete to delete the org """
        if not self.created:
            self.logger.info(
                "Skipping org deletion: the scratch org has not been created"
            )
            return

        p = sfdx("force:org:delete -p", self.username, "Deleting scratch org")

        stdout = []
        for line in p.stdout_text:
            stdout.append(line)
            if line.startswith("An error occurred deleting this org"):
                self.logger.error(line)
            else:
                self.logger.info(line)

        if p.returncode:
            message = f"Failed to delete scratch org: \n{''.join(stdout)}"
            raise ScratchOrgException(message)

        # Flag that this org has been deleted
        self.config["created"] = False
        self.config["username"] = None
        self.config["date_created"] = None

    def force_refresh_oauth_token(self):
        # Call force:org:display and parse output to get instance_url and
        # access_token
        p = sfdx("force:org:open -r", self.username, log_note="Refreshing OAuth token")

        stdout_list = [line.strip() for line in p.stdout_text]

        if p.returncode:
            self.logger.error(f"Return code: {p.returncode}")
            for line in stdout_list:
                self.logger.error(line)
            message = f"Message: {nl.join(stdout_list)}"
            raise ScratchOrgException(message)

    def refresh_oauth_token(self, keychain):
        """ Use sfdx force:org:describe to refresh token instead of built in OAuth handling """
        if hasattr(self, "_scratch_info"):
            # Cache the scratch_info for 1 hour to avoid unnecessary calls out
            # to sfdx CLI
            delta = datetime.datetime.utcnow() - self._scratch_info_date
            if delta.total_seconds() > 3600:
                del self._scratch_info

                # Force a token refresh
                self.force_refresh_oauth_token()

        # Get org info via sfdx force:org:display
        self.scratch_info
        # Get additional org info by querying API
        self._load_orginfo()
