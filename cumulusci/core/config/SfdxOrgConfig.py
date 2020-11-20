import datetime
import json

from cumulusci.core.config import OrgConfig
from cumulusci.core.exceptions import SfdxOrgException
from cumulusci.core.sfdx import sfdx
from cumulusci.utils import get_git_config

nl = "\n"  # fstrings can't contain backslashes


class SfdxOrgConfig(OrgConfig):
    """Org config which loads from sfdx keychain"""

    @property
    def sfdx_info(self):
        if hasattr(self, "_sfdx_info"):
            return self._sfdx_info

        # On-demand creation of scratch orgs
        if self.create_org is not None and not self.created:
            self.create_org()

        username = self.config.get("username")
        assert username is not None, "SfdxOrgConfig must have a username"

        self.logger.info(f"Getting org info from Salesforce CLI for {username}")

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
            raise SfdxOrgException(message)

        else:
            try:
                org_info = json.loads("".join(stdout_list))
            except Exception as e:
                raise SfdxOrgException(
                    "Failed to parse json from output.\n  "
                    f"Exception: {e.__class__.__name__}\n  Output: {''.join(stdout_list)}"
                )
            org_id = org_info["result"]["accessToken"].split("!")[0]

        sfdx_info = {
            "instance_url": org_info["result"]["instanceUrl"],
            "access_token": org_info["result"]["accessToken"],
            "org_id": org_id,
            "username": org_info["result"]["username"],
        }
        if org_info["result"].get("password"):
            sfdx_info["password"] = org_info["result"]["password"]
        self._sfdx_info = sfdx_info
        self._sfdx_info_date = datetime.datetime.utcnow()
        self.config.update(sfdx_info)

        sfdx_info.update(
            {
                "created_date": org_info["result"].get("createdDate"),
                "expiration_date": org_info["result"].get("expirationDate"),
            }
        )
        return sfdx_info

    @property
    def access_token(self):
        return self.sfdx_info["access_token"]

    @property
    def instance_url(self):
        return self.config.get("instance_url") or self.sfdx_info["instance_url"]

    @property
    def org_id(self):
        org_id = self.config.get("org_id")
        if not org_id:
            org_id = self.sfdx_info["org_id"]
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
            username = self.sfdx_info["username"]
        return username

    @property
    def password(self):
        password = self.config.get("password")
        if not password:
            password = self.sfdx_info["password"]
        return password

    @property
    def email_address(self):
        email_address = self.config.get("email_address")
        if not email_address:
            email_address = get_git_config("user.email")
            self.config["email_address"] = email_address

        return email_address

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
            raise SfdxOrgException(message)

    def refresh_oauth_token(self, keychain):
        """ Use sfdx force:org:describe to refresh token instead of built in OAuth handling """
        if hasattr(self, "_sfdx_info"):
            # Cache the sfdx_info for 1 hour to avoid unnecessary calls out to sfdx CLI
            delta = datetime.datetime.utcnow() - self._sfdx_info_date
            if delta.total_seconds() > 3600:
                del self._sfdx_info

                # Force a token refresh
                self.force_refresh_oauth_token()

        # Get org info via sfdx force:org:display
        self.sfdx_info
        # Get additional org info by querying API
        self._load_orginfo()
