import http
from pydantic import BaseModel
from pydantic import AnyUrl
from typing import Optional
from urllib.parse import quote

from cumulusci.core.exceptions import CumulusCIUsageError
from cumulusci.oauth.exceptions import OAuthError


class OAuthClientInfo(BaseModel):
    """Holds info for an OAuth client"""

    client_id: str
    client_secret: Optional[str]
    auth_uri: AnyUrl
    token_uri: AnyUrl
    callback_url: AnyUrl = "http://localhost:8080/callback"
    scope: str
    state: Optional[str]

    def get_auth_uri(self):
        """Returns the auth_url _plus_ all expected url parameters"""
        return self.auth_uri

    def get_token_uri(self):
        return self.token_uri

    def validate_response(self, response):
        """Subclasses can implement custom response validation"""
        if not response:
            raise CumulusCIUsageError("Authentication timed out or otherwise failed.")
        elif response.status_code == http.client.OK:
            return
        raise OAuthError(
            f"OAuth failed\nstatus_code: {response.status_code}\ncontent: {response.content}"
        )


class SalesforceOAuthClientInfo(OAuthClientInfo):
    """Information about a SalesforceOAuth client."""

    is_sandbox: bool
    prompt: str = "login"
    scope: str = "web full refresh_token"
    auth_uri: str = "https://{}.salesforce.com/services/oauth2/authorize"
    token_uri: str = "https://{}.salesforce.com/services/oauth2/token"

    def get_auth_uri(self):
        """Returns the auth_url plus all expected url parameters"""
        url = self.auth_uri.format("test" if self.is_sandbox else "login")
        url += "?response_type=code"
        url += f"&client_id={self.client_id}"
        url += f"&redirect_uri={self.callback_url}"
        url += f"&scope={quote(self.scope)}"
        url += f"&prompt={quote(self.prompt)}"
        return url

    def get_token_uri(self):
        return self.token_uri.format("test" if self.is_sandbox else "login")


class MarketingCloudOAuthConfig(OAuthClientInfo):
    pass
