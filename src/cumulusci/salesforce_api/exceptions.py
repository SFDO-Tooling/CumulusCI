from cumulusci.core.exceptions import CumulusCIException, CumulusCIFailure


class MetadataApiError(CumulusCIFailure):
    def __init__(self, message, response):
        super(MetadataApiError, self).__init__(message)
        self.response = response


class MetadataComponentFailure(MetadataApiError):
    pass


class MetadataParseError(MetadataApiError):
    pass


class MissingOAuthError(CumulusCIException):
    pass


class MissingOrgCredentialsError(CumulusCIException):
    pass
