from pydantic import AnyUrl
from pydantic import BaseModel
from typing import Optional


class OAuthClientInfo(BaseModel):
    """Holds info for an OAuth client"""

    client_id: str
    client_secret: Optional[str]
    auth_uri: AnyUrl
    token_uri: AnyUrl
    revoke_uri: Optional[AnyUrl]
    callback_url: AnyUrl = "http://localhost:8080/callback"
    scope: Optional[str]
    prompt: Optional[str]  # 'login' value required for OAuth to SF Org
    state: Optional[str]
