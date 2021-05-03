from cumulusci.core.config import ServiceConfig


class MarketingCloudServiceConfig(ServiceConfig):
    def __init__(self, oauth_client_name, config):
        self.access_token = None
        self.refresh_token = None
        self.oauth_client_service_name = oauth_client_name
        super().__init__(config=config)

    def connect():
        """Uses the access token to connect to a MC instance"""
        pass

    def refresh_token():
        """TODO: Is there a refresh flow for MC?"""
        pass
