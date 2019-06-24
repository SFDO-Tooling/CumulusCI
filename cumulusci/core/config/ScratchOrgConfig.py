from __future__ import unicode_literals
import datetime
import json
import os
import re

import sarge
from simple_salesforce import Salesforce

from cumulusci.utils import get_git_config
from cumulusci.core.sfdx import sfdx
from cumulusci.core.config import FAILED_TO_CREATE_SCRATCH_ORG
from cumulusci.core.config import OrgConfig
from cumulusci.core.exceptions import ScratchOrgException


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
            self.logger.error("Return code: {}".format(p.returncode))
            for line in stderr_list:
                self.logger.error(line)
            for line in stdout_list:
                self.logger.error(line)
            message = "\nstderr:\n{}".format("\n".join(stderr_list))
            message += "\nstdout:\n{}".format("\n".join(stdout_list))
            raise ScratchOrgException(message)

        else:
            try:
                org_info = json.loads("".join(stdout_list))
            except Exception as e:
                raise ScratchOrgException(
                    "Failed to parse json from output. This can happen if "
                    "your scratch org gets deleted.\n  "
                    "Exception: {}\n  Output: {}".format(
                        e.__class__.__name__, "".join(stdout_list)
                    )
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

        self._scratch_info_date = datetime.datetime.utcnow()

        return self._scratch_info

    @property
    def access_token(self):
        return self.scratch_info["access_token"]

    @property
    def instance_url(self):
        return self.scratch_info["instance_url"]

    @property
    def org_id(self):
        org_id = self.config.get("org_id")
        if not org_id:
            org_id = self.scratch_info["org_id"]
        return org_id

    @property
    def user_id(self):
        if not self.config.get("user_id"):
            sf = Salesforce(
                instance=self.instance_url.replace("https://", ""),
                session_id=self.access_token,
                version="38.0",
            )
            result = sf.query_all(
                "SELECT Id FROM User WHERE UserName='{}'".format(self.username)
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
    def expired(self):
        return self.expires and self.expires < datetime.datetime.now()

    @property
    def expires(self):
        if self.date_created:
            return self.date_created + datetime.timedelta(days=int(self.days))

    @property
    def days_alive(self):
        if self.expires:
            delta = datetime.datetime.now() - self.date_created
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

        options = {
            "config_file": self.config_file,
            "devhub": " --targetdevhubusername {}".format(self.devhub)
            if self.devhub
            else "",
            "namespaced": " -n" if not self.namespaced else "",
            "days": " --durationdays {}".format(self.days) if self.days else "",
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
        command = "force:org:create -f {config_file}{devhub}{namespaced}{days}{alias}{default} {email} {extraargs}".format(
            **options
        )
        p = sfdx(command, username=None, log_note="Creating scratch org")

        stderr = [line.strip() for line in p.stderr_text]
        stdout = [line.strip() for line in p.stdout_text]

        if p.returncode:
            message = "{}: \n{}\n{}".format(
                FAILED_TO_CREATE_SCRATCH_ORG, "\n".join(stdout), "\n".join(stderr)
            )
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

        self.config["date_created"] = datetime.datetime.now()

        if self.config.get("set_password"):
            self.generate_password()

        # Flag that this org has been created
        self.config["created"] = True

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
                "Failed to set password: \n{}\n{}".format(
                    "\n".join(stdout), "\n".join(stderr)
                )
            )

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
            message = "Failed to delete scratch org: \n{}".format("".join(stdout))
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
            self.logger.error("Return code: {}".format(p.returncode))
            for line in stdout_list:
                self.logger.error(line)
            message = "Message: {}".format("\n".join(stdout_list))
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
