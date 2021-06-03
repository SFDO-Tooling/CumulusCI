from urllib.parse import urlparse

from cumulusci.core.config.oauth2_service_config import OAuth2ServiceConfig


class MarketingCloudServiceConfig(OAuth2ServiceConfig):
    @property
    def tssd(self):
        """A dynamic value that represents the end user's subdomain.
        We can derive this value from either soap_instance_url or rest_instance_url
        which are present upon successful completion of an OAuth2 flow."""
        result = urlparse(self.config["rest_instance_url"])
        return result.netloc.split(".")[0]
