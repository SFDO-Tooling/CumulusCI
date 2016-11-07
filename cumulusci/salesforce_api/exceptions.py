class MetadataApiError(Exception):
    def __init__(self, message, response):
        super(MetadataApiError, self).__init__(message)
        self.response = response

class MissingOAuthError(Exception):
    pass

class MissingOrgCredentialsError(Exception):
    pass
