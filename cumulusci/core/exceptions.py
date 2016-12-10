class CumulusCIException(Exception):
    pass

class NotInProject(CumulusCIException):
    """ Raised when no project can be found in the current context """
    pass

class ProjectConfigNotFound(CumulusCIException):
    """ Raised when a project is found in the current context but no configuration was found for the project """
    pass

class KeychainKeyNotFound(CumulusCIException):
    """ Raised when the keychain key couldn't be found """

class KeychainConnectedAppNotFound(CumulusCIException):
    """ Raised when the connected app configuration couldn't be found for a keychain """

class OrgNotFound(CumulusCIException):
    """ Raised when no org could be found by a given name in the project keychain """
    pass

class ServiceNotConfigured(CumulusCIException):
    """ Raised when no service configuration could be found by a given name in the project keychain """
    pass

class ConfigError(CumulusCIException):
    """ Raised when a configuration enounters an error """
    pass

class AntTargetException(CumulusCIException):
    """ Raised when a generic Ant target error occurs """
    pass

class DeploymentException(CumulusCIException):
    """ Raised when a metadata api deployment error occurs """
    pass

class ApexTestException(CumulusCIException):
    """ Raised when a build fails because of an Apex test failure """
    pass

class SalesforceCredentialsException(CumulusCIException):
    """ Raise when Salesforce credentials are invalid """
    pass

class TaskRequiresSalesforceOrg(CumulusCIException):
    """ Raise when a task that requires a Salesforce org_config is not initialized with an org_config """
    pass

class TaskOptionsError(CumulusCIException):
    """ Raise when a task's options are invalid """
    pass

class GithubNotConfigured(CumulusCIException):
    """ Raise when attempting to get the Github configuration from the keychain and no configuration is set """
    pass

class MrbelvedereNotConfigured(CumulusCIException):
    """ Raise when attempting to get the mrbelvedere configuration from the keychain and no configuration is set """
    pass

class ApexTestsDBNotConfigured(CumulusCIException):
    """ Raise when attempting to get the ApexTestsDB configuration from the keychain and no configuration is set """
    pass

class TaskNotFoundError(CumulusCIException):
    """ Raise when task is not found in project config """
    pass

class FlowNotFoundError(CumulusCIException):
    """ Raise when flow is not found in project config """
    pass

class MrbelvedereError(CumulusCIException):
    """ Raise for errors from mrbelvedere installer """
    pass

class ApextestsdbError(CumulusCIException):
    """ Raise for errors from apextestsdb """
    pass

class ScratchOrgException(CumulusCIException):
    """ Raise for errors related to scratch orgs """
    pass

class GithubException(CumulusCIException):
    """ Raise for errors related to GitHub """
    pass

class SalesforceException(CumulusCIException):
    """ Raise for errors related to Salesforce """
    pass

class SalesforceDXException(CumulusCIException):
    """ Raise for errors related to Salesforce DX """
    pass

class SOQLQueryException(CumulusCIException):
    """ Raise for errors related to Salesforce DX """
    pass
