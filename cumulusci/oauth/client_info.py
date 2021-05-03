from pydantic import BaseModel
from pydantic import AnyUrl
from typing import Optional


class OAuthClientInfo(BaseModel):
    """Holds info for an OAuth client"""

    client_id: str
    client_secret: Optional[str]
    auth_uri: AnyUrl
    token_uri: AnyUrl
    revoke_uri: AnyUrl
    callback_url: AnyUrl = "http://localhost:8080/callback"
    scope: str
    prompt: Optional[str]  # required for SF
    state: Optional[str]
