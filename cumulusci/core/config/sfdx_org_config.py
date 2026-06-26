import datetime
import json
from json.decoder import JSONDecodeError

from cumulusci.core.config import OrgConfig
from cumulusci.core.exceptions import SfdxOrgException
from cumulusci.core.sfdx import sfdx, shell_quote
from cumulusci.utils import get_git_config

nl = "\n"  # fstrings can't contain backslashes

# Prefix of the sentinel string that SF CLI 2.136+ writes in place of
# credential fields when SF_TEMP_SHOW_SECRETS is unset. See
# @salesforce/plugin-org messages/secrets-redacted.md for the canonical
# strings. Prefix-only matching avoids coupling to the English suffix.
# The trailing space is load-bearing: the CLI sentinel is the literal
# "[REDACTED] Use ..." form, never "[REDACTED]Use ...".
#
# Locale fragility: today `@salesforce/core`'s Messages.getLocale() is
# hardcoded to en_US (per-locale message bundles are an unimplemented
# TODO upstream), so this prefix is stable on every shipping CLI. The
# "[REDACTED] " literal lives inside the translatable message string,
# however; if Salesforce later wires up localization, a non-English
# `redacted.accessToken` could drop this prefix and silently break
# detection. A locale-independent signal (matching the three sentinel
# message keys, or "value is not a well-formed access token") would be
# more robust if/when that lands.
_REDACTED_PREFIX = "[REDACTED] "


def _is_sentinel(value):
    """True only for the SF CLI 2.136+ redaction sentinel string."""
    return isinstance(value, str) and value.startswith(_REDACTED_PREFIX)


def _is_redacted(value):
    """True when the CLI returned an absent/empty value or the redaction sentinel.

    Used for the access-token path: an absent token is as actionable as a redacted
    one (both mean "ask `sf org auth show-access-token`"). For the password path,
    prefer _is_sentinel so a legitimately-absent password (passwordless org on a
    new CLI) does not trigger a pointless `sf org auth show-user-password` call.
    """
    if not value:
        return True
    return _is_sentinel(value)


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
            result = org_info["result"]

        org_id = result.get("id")
        if not org_id:
            raise SfdxOrgException(
                "Salesforce CLI did not return an org id from `sf org display`. "
                "Please re-authenticate with `sf org login`."
            )

        access_token = result.get("accessToken")
        if _is_redacted(access_token):
            access_token = self._fetch_access_token(username)

        password = result.get("password")
        # Gate the password fallback on the sentinel ONLY. An absent password
        # means the org has no password (web-auth sandbox, scratch org without
        # `force:user:password:generate`); calling `sf org auth show-user-password`
        # in that case is a pointless extra subprocess on every refresh.
        if _is_sentinel(password):
            password = self._fetch_user_password(username)

        sfdx_info = {
            "instance_url": result["instanceUrl"],
            "access_token": access_token,
            "org_id": org_id,
            "username": result["username"],
        }
        if password:
            sfdx_info["password"] = password
        self._sfdx_info = sfdx_info
        self._sfdx_info_date = datetime.datetime.utcnow()
        self.config.update(sfdx_info)

        sfdx_info.update(
            {
                "created_date": result.get("createdDate"),
                "expiration_date": result.get("expirationDate"),
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

        p = sfdx(f"org display --target-org={shell_quote(username)} --json")
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

        info = json.loads(p.stdout_text.read())
        token = info.get("result", {}).get("accessToken")
        if _is_redacted(token):
            return self._fetch_access_token(username)
        return token

    def _fetch_access_token(self, username):
        """Retrieve an access token using `sf org auth show-access-token`.

        Used as a fallback when `sf org display` redacts the token (SF CLI 2.136+).
        """
        p = sfdx(
            f"org auth show-access-token --target-org={shell_quote(username)}"
            f" --json --no-prompt"
        )
        output = p.stdout_text.read()
        if p.returncode:
            try:
                explanation = json.loads(output).get("message", output)
            except JSONDecodeError:
                explanation = output
            raise SfdxOrgException(
                f"Unable to retrieve access token for {username}. "
                f"Tried `sf org display` and `sf org auth show-access-token`. "
                f"Try running `sf org login` or upgrading the Salesforce CLI.\n"
                f"{explanation}"
            )
        try:
            info = json.loads(output)
        except JSONDecodeError as e:
            raise SfdxOrgException(
                f"Failed to parse JSON from `sf org auth show-access-token`: {e}"
            )
        token = info.get("result", {}).get("accessToken")
        if _is_redacted(token):
            # Defensive: if show-access-token itself ever returns a sentinel,
            # treat it as failure rather than handing back a placeholder.
            raise SfdxOrgException(
                f"Unable to retrieve access token for {username}. "
                f"Tried `sf org display` and `sf org auth show-access-token`. "
                f"Try running `sf org login` or upgrading the Salesforce CLI."
            )
        return token

    def _fetch_user_password(self, username):
        """Retrieve the org password using `sf org auth show-user-password`.

        Used as a fallback when `sf org display` redacts the password (SF CLI
        2.136+). Returns None on any failure path (non-zero exit, malformed
        JSON, sentinel result) since the password is optional. Failures are
        logged at debug level so transient issues can be diagnosed without
        promoting the call to raise.
        """
        p = sfdx(
            f"org auth show-user-password --target-org={shell_quote(username)}"
            f" --json --no-prompt"
        )
        if p.returncode:
            self.logger.debug(
                f"sf org auth show-user-password exited {p.returncode} for "
                f"{username}; treating as no password."
            )
            return None
        try:
            info = json.loads(p.stdout_text.read())
        except JSONDecodeError as e:
            self.logger.debug(
                f"Failed to parse JSON from sf org auth show-user-password "
                f"for {username}: {e}. Treating as no password."
            )
            return None
        password = info.get("result", {}).get("password")
        if _is_redacted(password):
            return None
        return password

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
            delta = datetime.datetime.utcnow() - self._sfdx_info_date
            if delta.total_seconds() > 3600:
                del self._sfdx_info

                # Force a token refresh
                self.force_refresh_oauth_token()
        self.print_json = print_json
        # Get org info via sf org display
        self.sfdx_info
        # Get additional org info by querying API
        self._load_orginfo()
