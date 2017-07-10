from cumulusci.core.exceptions import CumulusCIException


class GithubApiError(CumulusCIException):
    pass


class GithubApiNotFoundError(CumulusCIException):
    pass


class GithubApiNoResultsError(CumulusCIException):
    pass


class GithubApiUnauthorized(CumulusCIException):
    pass


class GithubIssuesError(CumulusCIException):
    pass

class LastReleaseTagNotFoundError(CumulusCIException):
    pass
