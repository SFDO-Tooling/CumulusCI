import base64
import json
import os
import pickle

from Crypto import Random
from Crypto.Cipher import AES

from cumulusci.core.config import BaseConfig
from cumulusci.core.config import ConnectedAppOAuthConfig
from cumulusci.core.config import OrgConfig
from cumulusci.core.config import GithubConfig
from cumulusci.core.config import MrbelvedereConfig
from cumulusci.core.config import ApexTestsDBConfig
from cumulusci.core.exceptions import OrgNotFound
from cumulusci.core.exceptions import KeychainConnectedAppNotFound
from cumulusci.core.exceptions import ApexTestsDBNotConfigured
from cumulusci.core.exceptions import GithubNotConfigured
from cumulusci.core.exceptions import MrbelvedereNotConfigured
from cumulusci.oauth.salesforce import SalesforceOAuth2

class BaseProjectKeychain(BaseConfig):
    def __init__(self, project_config, key):
        super(BaseProjectKeychain, self).__init__()
        self.config = {
            'orgs': {}, 
            'app': None, 
            'github': None, 
            'mrbelvedere': None, 
            'apextestsdb': None, 
        }
        self.project_config = project_config
        self.key = key
        self._load_keychain()

    def _load_keychain(self):
        """ Subclasses can override to implement logic to load the keychain """
        pass

    def change_key(self, key):
        connected_app = self.get_connected_app()
        github = self.get_github()
        mrbelvedere = self.get_mrbelvedere()
        apextestsdb = self.get_apextestsdb()
        orgs = {}
        for org_name in self.list_orgs():
            orgs[org_name] = self.get_org(org_name)

        self.key = key
        if connected_app:
            self.set_connected_app(connected_app)

        if orgs:
            for org_name, org_config in orgs.items():
                self.set_org(org_name, org_config)

        if github:
            self.set_github(github)

        if mrbelvedere:
            self.set_mrbelvedere(mrbelvedere)

        if apextestsdb:
            self.set_apextestsdb(apextestsdb)

    def set_connected_app(self, app_config):
        self._set_connected_app(app_config)
        self._load_keychain()
    
    def _set_connected_app(self, app_config):
        self.app = app_config

    def get_connected_app(self):
        return self._get_connected_app()

    def _get_connected_app(self):
        return self.app

    def set_org(self, name, org_config):
        self._set_org(name, org_config)
        self._load_keychain()

    def _set_org(self, name, org_config):
        self.orgs[name] = org_config

    def get_default_org(self):
        for org in self.list_orgs():
            org_config = self.get_org(org)
            if org_config.default:
                return org_config

    def set_default_org(self, name):
        org = self.get_org(name)
        self.unset_default_org()
        org.config['default'] = True
        self.set_org(name, org)
        
    def unset_default_org(self):
        for org in self.list_orgs():
            org_config = self.get_org(org)
            if org_config.default:
                del org_config.config['default']
                self.set_org(org, org_config)

    def get_org(self, name):
        if name not in self.orgs:
            self._raise_org_not_found(name)
        return self._get_org(name)

    def _get_org(self, name):
        return self.orgs.get(name)
    
    def _raise_org_not_found(self, name):
        raise OrgNotFound('Org named {} was not found in keychain'.format(name))

    def list_orgs(self):
        orgs = self.orgs.keys()
        orgs.sort()
        return orgs

    def get_github(self):
        github = self._get_github()
        if not github:
            raise GithubNotConfigured("Github is not configured on the keychain.  Configure Github in the keychain and try again")
        return github

    def _get_github(self):
        return self.github

    def set_github(self, github_config):
        #if not isinstance(github_config, GithubConfig):
        #    raise TypeError('github_config must be an instance of cumulusci.core.config.GithubConfig')
        return self._set_github(github_config)
       
    def _set_github(self, github_config):
        self.config['github'] = github_config

    def get_mrbelvedere(self):
        mrbelvedere = self._get_mrbelvedere()
        if not mrbelvedere:
            raise MrbelvedereNotConfigured("mrbelvedere is not configured on the keychain.  Configure mrbelvedere in the keychain and try again")
        return mrbelvedere

    def _get_mrbelvedere(self):
        return self.mrbelvedere

    def set_mrbelvedere(self, mrbelvedere_config):
        #if not isinstance(mrbelvedere_config, MrbelvedereConfig):
        #    raise TypeError('mrbelvedere_config must be an instance of cumulusci.core.config.MrbelvedereConfig')
        return self._set_mrbelvedere(mrbelvedere_config)

    def _set_mrbelvedere(self, mrbelvedere_config):
        self.config['mrbelvedere'] = mrbelvedere_config

    def get_apextestsdb(self):
        apextestsdb = self._get_apextestsdb()
        if not apextestsdb:
            raise ApexTestsDBNotConfigured("ApexTestsDB is not configured on the keychain.  Configure ApexTestsDB in the keychain and try again")
        return apextestsdb

    def _get_apextestsdb(self):
        return self.apextestsdb

    def set_apextestsdb(self, apextestsdb_config):
        #if not isinstance(apextestsdb_config, ApexTestsDBConfig):
        #    raise TypeError('apextestsdb_config must be an instance of cumulusci.core.config.ApexTestsDBConfig')
        return self._set_apextestsdb(apextestsdb_config)

    def _set_apextestsdb(self, apextestsdb_config):
        self.config['apextestsdb'] = apextestsdb_config

class EnvironmentProjectKeychain(BaseProjectKeychain):
    """ A project keychain that stores org credentials in environment variables """ 
    org_var_prefix = 'CUMULUSCI_ORG_'
    app_var = 'CUMULUSCI_CONNECTED_APP'
    github_var = 'CUMULUSCI_GITHUB'
    mrbelvedere_var = 'CUMULUSCI_MRBELVEDERE'
    apextestsdb_var = 'CUMULUSCI_APEXTESTSDB'
   
    def _load_keychain(self): 
        self._load_keychain_app()
        self._load_keychain_orgs()
        self._load_keychain_github()
        self._load_keychain_mrbelvedere()
        self._load_keychain_apextestsdb()

    def _load_keychain_app(self):
        app = os.environ.get(self.app_var)
        if app:
            self.app = ConnectedAppOAuthConfig(json.loads(app))

    def _load_keychain_orgs(self):
        for key, value in os.environ.items():
            if key.startswith(self.org_var_prefix):
                self.orgs[key[len(self.org_var_prefix):]] = OrgConfig(json.loads(value))

    def _load_keychain_github(self):
        github = os.environ.get(self.github_var)
        if github:
            self.github = GithubConfig(json.loads(github))

    def _load_keychain_mrbelvedere(self):
        mrbelvedere = os.environ.get(self.mrbelvedere_var)
        if mrbelvedere:
            self.mrbelvedere = MrbelvedereConfig(json.loads(mrbelvedere))

    def _load_keychain_apextestsdb(self):
        apextestsdb = os.environ.get(self.apextestsdb_var)
        if apextestsdb:
            self.apextestsdb = ApexTestsDBConfig(json.loads(apextestsdb))


BS = 16
pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS)
unpad = lambda s : s[0:-ord(s[-1])]

class BaseEncryptedProjectKeychain(BaseProjectKeychain):
    """ Base class for building project keychains that use AES encryption for securing stored org credentials """

    def _set_connected_app(self, app_config):
        encrypted = self._encrypt_config(app_config)
        self._set_encrypted_connected_app(encrypted)

    def _set_encrypted_connected_app(self, encrypted):
        self.app = encrypted

    def _get_connected_app(self):
        if self.app:
            return self._decrypt_config(ConnectedAppOAuthConfig, self.app)

    def _set_github(self, github_config):
        encrypted = self._encrypt_config(github_config)
        self._set_encrypted_github(encrypted)

    def _set_encrypted_github(self, encrypted):
        self.github = encrypted

    def _get_github(self):
        if self.github:
            return self._decrypt_config(GithubConfig, self.github)

    def _set_mrbelvedere(self, mrbelvedere_config):
        encrypted = self._encrypt_config(mrbelvedere_config)
        self._set_encrypted_mrbelvedere(encrypted)

    def _set_encrypted_mrbelvedere(self, encrypted):
        self.mrbelvedere = encrypted

    def _get_mrbelvedere(self):
        if self.mrbelvedere:
            return self._decrypt_config(MrbelvedereConfig, self.mrbelvedere)

    def _set_apextestsdb(self, apextestsdb_config):
        encrypted = self._encrypt_config(apextestsdb_config)
        self._set_encrypted_apextestsdb(encrypted)

    def _set_encrypted_apextestsdb(self, encrypted):
        self.apextestsdb = encrypted

    def _get_apextestsdb(self):
        if self.apextestsdb:
            return self._decrypt_config(ApexTestsDBConfig, self.apextestsdb)

    def _set_org(self, name, org_config):
        encrypted = self._encrypt_config(org_config)
        self._set_encrypted_org(name, encrypted)

    def _set_encrypted_org(self, name, encrypted):
        self.orgs[name] = encrypted

    def _get_org(self, name):
        return self._decrypt_config(OrgConfig, self.orgs[name])

    def _get_cipher(self, iv=None):
        if iv is None:
            iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return cipher, iv

    def _encrypt_config(self, config):
        pickled = pickle.dumps(config.config)
        pickled = pad(pickled)
        #pickled = base64.b64encode(pickled)
        cipher, iv = self._get_cipher()
        return base64.b64encode(iv + cipher.encrypt(pickled))

    def _decrypt_config(self, config_class, encrypted_config):
        if not encrypted_config:
            return config_class()
        encrypted_config = base64.b64decode(encrypted_config)
        iv = encrypted_config[:16]
        cipher, iv = self._get_cipher(iv)
        pickled = cipher.decrypt(encrypted_config[16:])
        return config_class(pickle.loads(pickled))

class EncryptedFileProjectKeychain(BaseEncryptedProjectKeychain):
    """ An encrypted project keychain that stores in the project's local directory """

    @property
    def project_local_dir(self):
        return self.project_config.project_local_dir

    def _load_keychain(self):
        if not self.project_local_dir: 
            return

        for item in os.listdir(self.project_local_dir):
            if item.endswith('.org'):
                f_item = open(os.path.join(self.project_local_dir, item), 'r')
                org_name = item.replace('.org', '')
                org_config = f_item.read()
                self.config['orgs'][org_name] = org_config
            elif item == 'connected.app':
                f_item = open(os.path.join(self.project_local_dir, item), 'r')
                app_config = f_item.read()
                self.config['app'] = app_config
            elif item == 'github.config':
                f_item = open(os.path.join(self.project_local_dir, item), 'r')
                github_config = f_item.read()
                self.config['github'] = github_config
            elif item == 'mrbelvedere.config':
                f_item = open(os.path.join(self.project_local_dir, item), 'r')
                mrbelvedere_config = f_item.read()
                self.config['mrbelvedere'] = mrbelvedere_config
            elif item == 'apextestsdb.config':
                f_item = open(os.path.join(self.project_local_dir, item), 'r')
                apextestsdb_config = f_item.read()
                self.config['apextestsdb'] = apextestsdb_config

    def _set_encrypted_connected_app(self, encrypted):
        f_org = open(os.path.join(self.project_local_dir, 'connected.app'), 'w')
        f_org.write(encrypted)
        f_org.close()
        self.app = encrypted

    def _set_encrypted_github(self, encrypted):
        f_org = open(os.path.join(self.project_local_dir, 'github.config'), 'w')
        f_org.write(encrypted)
        f_org.close()
        self.github = encrypted

    def _set_encrypted_mrbelvedere(self, encrypted):
        f_org = open(os.path.join(self.project_local_dir, 'mrbelvedere.config'), 'w')
        f_org.write(encrypted)
        f_org.close()
        self.mrbelvedere = encrypted

    def _set_encrypted_apextestsdb(self, encrypted):
        f_org = open(os.path.join(self.project_local_dir, 'apextestsdb.config'), 'w')
        f_org.write(encrypted)
        f_org.close()
        self.apextestsdb = encrypted

    def _set_encrypted_org(self, name, encrypted):
        f_org = open(os.path.join(self.project_local_dir, '{}.org'.format(name)), 'w')
        f_org.write(encrypted)
        f_org.close()

    def _raise_org_not_found(self, name):
        raise OrgNotFound(
            'Org information could not be found.  Expected to find encrypted file at {}/{}.org'.format(
                self.project_local_dir, 
                name
            )
        )
