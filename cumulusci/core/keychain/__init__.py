# IMPORT ORDER MATTERS!

# inherit from BaseConfig
from cumulusci.core.keychain.BaseProjectKeychain import BaseProjectKeychain
from cumulusci.core.keychain.BaseProjectKeychain import DEFAULT_CONNECTED_APP

# inherit from BaseProjectKeychain
from cumulusci.core.keychain.BaseEncryptedProjectKeychain import (
    BaseEncryptedProjectKeychain,
)
from cumulusci.core.keychain.EnvironmentProjectKeychain import (
    EnvironmentProjectKeychain,
)

# inherit from BaseEncryptedProjectKeychain
from cumulusci.core.keychain.EncryptedFileProjectKeychain import (
    EncryptedFileProjectKeychain,
)
