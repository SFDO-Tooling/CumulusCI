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

