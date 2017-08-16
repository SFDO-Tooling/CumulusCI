from cumulusci.core.exceptions import CumulusCIException


class GithubIssuesError(CumulusCIException):
    pass

class LastReleaseTagNotFoundError(CumulusCIException):
    pass
