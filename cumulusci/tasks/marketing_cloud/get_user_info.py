import json

import requests

from .base import BaseMarketingCloudTask


class GetUserInfoTask(BaseMarketingCloudTask):
    """Retrieves user info of pertaining to the currently logged in user.
    Sanitizes and returns the payload in self.return_values."""

    def _run_task(self):
        try:
            payload = self.mc_config.get_user_info()
        except requests.exceptions.HTTPError as e:
            self.logger.error(
                f"Exception occurred fetching user info: {e.response.text if e.response else 'None'}"
            )
            raise

        payload = self._sanitize_payload(payload)
        self.logger.info("Successfully fetched user info.")
        self.logger.info(json.dumps(payload, indent=4))

        self.return_values = payload

    def _sanitize_payload(self, payload: dict) -> dict:
        """Removes any sensitive or non-pertinent information from the payload.
        This currently includes the following top-level portions of the response:
        (1) rest
        (2) application
        (3) permissions

        See the following for a comprehensive response example:
        https://developer.salesforce.com/docs/marketing/marketing-cloud/guide/getUserInfo.html
        """
        del payload["rest"]
        del payload["application"]
        del payload["permissions"]
        return payload
