class SalesforceOAuthError(Exception):
    pass

class RequestOauthTokenError(Exception):
    def __init__(self, message, response):
        super(RequestOauthTokenError, self).__init__(message)
        self.response = response
