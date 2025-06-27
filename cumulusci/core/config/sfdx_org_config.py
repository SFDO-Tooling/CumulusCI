import datetime
import json
from json.decoder import JSONDecodeError

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
        if self.createable and not self.created:
            self.create_org()

        username = self.config.get("username")
        assert username is not None, "SfdxOrgConfig must have a username"
        if not self.print_json:
            self.logger.info(f"Getting org info from Salesforce CLI for {username}")

        # Call org display and parse output to get instance_url and
        # access_token
        p = sfdx("org display --json", self.username)

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
        self._sfdx_info_date = datetime.datetime.now(datetime.timezone.utc)
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

    def get_access_token(self, **userfields):
        """Get the access token for a specific user

        If no keyword arguments are passed in, this will return the
        access token for the default user. If userfields has the key
        "username", the access token for that user will be returned.
        Otherwise, a SOQL query will be made based off of the
        passed-in fields to find the username, and the token for that
        username will be returned.

        Examples:

        | # default user access token:
        | token = org.get_access_token()

        | # access token for 'test@example.com'
        | token = org.get_access_token(username='test@example.com')

        | # access token for user based on lookup fields
        | token = org.get_access_token(alias='dadvisor')

        """
        if not userfields:
            # No lookup fields specified? Return the token for the default user
            return self.access_token

        # if we have a username, use it. Otherwise we need to do a
        # lookup using the passed-in fields.
        username = userfields.get("username", None)
        if username is None:
            where = [f"{key} = '{value}'" for key, value in userfields.items()]
            query = f"SELECT Username FROM User WHERE {' AND '.join(where)}"
            result = self.salesforce_client.query_all(query).get("records", [])
            if len(result) == 0:
                raise SfdxOrgException(
                    "Couldn't find a username for the specified user."
                )
            elif len(result) > 1:
                raise SfdxOrgException(
                    "More than one user matched the search critiera."
                )
            else:
                username = result[0]["Username"]

        p = sfdx(f"org display --target-org={username} --json")
        if p.returncode:
            output = p.stdout_text.read()
            try:
                info = json.loads(output)
                explanation = info["message"]
            except (JSONDecodeError, KeyError):
                explanation = output

            raise SfdxOrgException(
                f"Unable to find access token for {username}\n{explanation}"
            )
        else:
            info = json.loads(p.stdout_text.read())
            return info["result"]["accessToken"]

    def force_refresh_oauth_token(self):
        # Call org display and parse output to get instance_url and
        # access_token
        p = sfdx("org open -r", self.username, log_note="Refreshing OAuth token")

        stdout_list = [line.strip() for line in p.stdout_text]

        if p.returncode:
            self.logger.error(f"Return code: {p.returncode}")
            for line in stdout_list:
                self.logger.error(line)
            message = f"Message: {nl.join(stdout_list)}"
            raise SfdxOrgException(message)

    # Added a print json argument to check whether it is there or not
    def refresh_oauth_token(self, keychain, print_json=False):
        """Use sfdx org display to refresh token instead of built in OAuth handling"""
        if hasattr(self, "_sfdx_info"):
            # Cache the sfdx_info for 1 hour to avoid unnecessary calls out to sfdx CLI
            if self._sfdx_info_date.tzinfo is None:
                # For naive _sfdx_info_date, use naive local time for consistent comparison
                now = datetime.datetime.now()
            else:
                # For timezone-aware _sfdx_info_date, use timezone-aware UTC time
                now = datetime.datetime.now(datetime.timezone.utc)
            delta = now - self._sfdx_info_date
            if delta.total_seconds() > 3600:
                del self._sfdx_info

                # Force a token refresh
                self.force_refresh_oauth_token()
        self.print_json = print_json
        # Get org info via sf org display
        self.sfdx_info
        # Get additional org info by querying API
        self._load_orginfo()
