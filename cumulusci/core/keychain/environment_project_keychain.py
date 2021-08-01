from cumulusci.core.keychain.encrypted_file_project_keychain import (
    EncryptedFileProjectKeychain,
)

# All logic for loading orgs and services from the environment
# now lives in EncryptedFileProjectKeychain.
EnvironmentProjectKeychain = EncryptedFileProjectKeychain  # pragma: no cover
