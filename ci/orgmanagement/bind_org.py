import base64
import time
from abc import abstractmethod, ABCMeta

import github
import yaml


class OrgBoundException(Exception):
    pass


class OrgManagementCommand(object):
    __metaclass__ = ABCMeta

    class BindBuildStorage(object):

        @property
        def config(self):
            return self.__config

        @config.setter
        def config(self, value):
            assert isinstance(value, dict), 'Config is not a dictionary'
            self.__config = value

        def __init__(self, config):
            self.config = config
            self._configure()

        def _get_config_attr(self, config_attr_name, default=None):
            if self.config.has_key(config_attr_name):
                return self.config[config_attr_name]
            elif default is not None:
                return default
            else:
                raise KeyError('Config attribute ' + config_attr_name + ' does not exist in config and default for this '
                                                                        'attribute is none')

        @abstractmethod
        def _configure(self):
            """Configure the storage"""
            pass

        @abstractmethod
        def get_binding(self, orgname):
            """Returns the build ID related to this orgname. Returns None if the orgname is not bound"""
            pass

        @abstractmethod
        def bind_build_to_org(self, orgname, build_id):
            """Binds a build to a given org"""
            pass

        @abstractmethod
        def delete_binding(self, org_name):
            """Removes a binding"""
            pass

    class GitFileStorage(BindBuildStorage):

        DEFAULT_STORAGE_BRANCHE = 'build_storage'
        DEFAULT_STORAGE_FILE = 'org_bindings'

        def __init__(self, config):
            self._bindings = dict()
            self._repo = None
            self._bindings_file = None
            super(OrgManagementCommand.GitFileStorage, self).__init__(config)

        def _configure(self):
            self._get_github_repo()
            self._load_bindings()

        def _get_github_repo(self):
            self._github = github.Github(self.config['GITHUB_USERNAME'], self.config['GITHUB_PASSWORD'])
            self._org = self._get_github_organization()
            self._repo = self._org.get_repo(self.config['GITHUB_REPO_NAME'])

        def _get_github_organization(self):
            try:
                org = self._github.get_organization(self.config['GITHUB_ORG_NAME'])
            except:
                org = self._github.get_user(self.config['GITHUB_USERNAME'])
            return org

        def _load_bindings(self):
            path = self._get_github_path()
            # get the file from github
            try:
                self._bindings_file = self._repo.get_file_contents(path, self._get_github_branch_name())
                # load the bindings (yaml content)
                decoded_content = self._bindings_file.decoded_content
                self._bindings = yaml.safe_load(decoded_content)
            except:
                self._bindings_file = None

        def _get_github_path(self):
            file_name = '/' + self._get_config_attr('BUILD_STORAGE_FILE',
                                              OrgManagementCommand.GitFileStorage.DEFAULT_STORAGE_FILE)
            path = file_name
            return path

        def get_binding(self, orgname):
            # type: (object) -> object
            binding = None
            if self._bindings.has_key(orgname):
                binding = self._bindings[orgname]
            return binding

        def bind_build_to_org(self, orgname, build_id):
            self._bindings[orgname] = build_id
            self._save_bindings()

        def delete_binding(self, org_name):
            del self._bindings[org_name]
            self._save_bindings()

        def _save_bindings(self):
            """precondition: already tried to load the file (and thus set _bindings_file)"""
            decoded_content = yaml.safe_dump(self._bindings)
            if self._bindings_file is None: # create the file
                self._create_bindings_file(decoded_content)
            else:
                self._repo.update_file(self._get_github_path(), '--skip-ci', decoded_content,
                                       self._get_github_branch_name())

        def _create_bindings_file(self, decoded_content):
            branch = None
            try:
                branch = self._repo.get_branch(self._get_github_branch_name())
            except:
                # create the branch
                branch = self._create_branch()
            self._repo.create_file(self._get_github_path(), '--skip-ci', decoded_content, branch.name)



        def _get_github_branch_name(self):
            branch = self._get_config_attr('BUILD_STORAGE_BRANCH',
                                           OrgManagementCommand.GitFileStorage.DEFAULT_STORAGE_BRANCHE)
            return branch

        def _create_branch(self):
            # get the latest commit (sha) from default branch
            default_branch_name = self._repo.default_branch
            default_branch = self._repo.get_branch(default_branch_name)
            latest_sha = default_branch.commit.sha
            # make a branch from head
            self._repo.create_git_ref('refs/heads/' + self._get_github_branch_name(), latest_sha)
            branch = self._repo.get_branch(self._get_github_branch_name())
            return branch

    @property
    def storage(self):
        return self.__storage

    @storage.setter
    def storage(self, value):
        assert isinstance(value, OrgManagementCommand.BindBuildStorage), 'storage is not of type BindBuildStorage'
        self.__storage = value

    @property
    def orgname(self):
        return self.__orgname

    @orgname.setter
    def orgname(self, value):
        assert isinstance(value, str), 'org_name is not a string'
        self.__orgname = value

    @abstractmethod
    def execute(self):
        pass

    def __init__(self, orgname, storage_config, storage_type='GITFILE'):
        self.__orgname = orgname
        self.__storage = self._get_storage(storage_type, storage_config)

    def _get_storage(self, storage_type, storage_config):
        storage = None
        if storage_type == 'GITFILE':
            storage = OrgManagementCommand.GitFileStorage(storage_config)
        else:
            raise OrgBoundException('Unknown storage type: ' + storage_type)
        return storage


class BindBuildToOrgCommand(OrgManagementCommand):

    @property
    def build_id(self):
        return self.__build_id

    @build_id.setter
    def build_id(self, value):
        assert isinstance(value, str), 'build_id is not a string'
        self.__build_id = value

    @property
    def wait(self):
        return self.__wait

    @wait.setter
    def wait(self, value):
        assert isinstance(value, bool), 'wait is not a boolean'
        self.__wait = value

    @property
    def sandbox(self):
        return self.__sandbox

    @sandbox.setter
    def sandbox(self, value):
        assert isinstance(value, bool), 'sandbox is not a boolean'
        self.__sandbox = value

    @property
    def retry_attempts(self):
        return self.__retry_attempts

    @retry_attempts.setter
    def retry_attempts(self, value):
        assert isinstance(value, int), 'retry_attempts is not an integer'
        assert value > 0, 'retry_attempts need to be greater than 0'
        self.__retry_attempts = value

    @property
    def sleeping_time(self):
        return self.__sleeping_time

    @sleeping_time.setter
    def sleeping_time(self, value):
        assert isinstance(value, int), 'sleeping_time is not an integer'
        assert value > 0, 'sleeping_time need to be greater than 0'
        self.__sleeping_time = value

    def __init__(self, orgname, build_id,  storage_config, storage_type='GITFILE'):
        super(BindBuildToOrgCommand, self).__init__(orgname, storage_config, storage_type)
        self.__build_id = build_id
        self.__sandbox = False
        self.__wait = True
        self.__retry_attempts = 10
        self.__sleeping_time = 360

    def execute(self):
        binding = self.storage.get_binding(self.orgname) # returns the build id bound to the org
        if binding is None: # the org is not bound yet
            self.storage.bind_build_to_org(self.orgname, self.build_id)
        elif binding == self.build_id: # accidentally tried to rebind the org to the build
            pass
        elif self.wait: # we need to wait or fail
            if self.retry_attempts > 0:
                time.sleep(self.sleeping_time)
                self.__retry_attempts = self.__retry_attempts - 1
                self.execute()
            else:
                raise OrgBoundException('Org ' + self.orgname + ' bound to build ' + binding + ' not released in time '
                                        'to bind org to new build ' + self.build_id)
        else:
            raise OrgBoundException('Org ' + self.orgname + ' bound to build ' + binding)


class ReleaseOrgCommand(OrgManagementCommand):

    def __init__(self, org_name, storage_config, binding=None, storage_type='GITFILE'):
        super(ReleaseOrgCommand, self).__init__(org_name, storage_config, storage_type)
        self._binding = binding

    @property
    def binding(self):
        return self._binding

    @binding.setter
    def binding(self, value):
        self._binding = value

    def execute(self):
        binding = self.storage.get_binding(self.orgname)
        if binding is None:
            raise OrgBoundException('Org ' + self.orgname + ' not bound')
        elif self.binding and self.binding != binding:
            raise OrgBoundException('Org ' + self.orgname + ' is bound to another build ' + binding)
        else:
            self.storage.delete_binding(self.orgname)

















