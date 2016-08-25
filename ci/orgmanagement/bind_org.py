import time
import os
import github
import urllib


class OrgBoundException(Exception):
    pass


class AbstractStorage(object):

    def __init__(self, config):
        self._config = config
        self._configure()

    def _configure(self):
        """subclasses should implement this to configure itself. Called from the __init__ method"""
        pass

    def bind_org(self, orgname, sandbox=False, wait=True, retry_attempts=10, sleeping_time=360):
        """reserves an org with the given orgname for use until released"""
        raise NotImplemented

    def release_org(self, orgname):
        """releases an org so it can be used again"""
        raise NotImplemented


class GithubTagStorage(AbstractStorage):

    def _configure(self):
        self._github = github.Github(self._config['GITHUB_USERNAME'], self._config['GITHUB_PASSWORD'])
        self._org = self._get_github_organization()
        self._repo = self._org.get_repo(self._config['GITHUB_REPO_NAME'])
        self._sha = self._config['SHA']

    def _get_github_organization(self):
        try:
            org = self._github.get_organization(self._config['GITHUB_ORG_NAME'])
        except:
            org = self._github.get_user(self._config['GITHUB_USERNAME'])
        return org

    def bind_org(self, orgname, sandbox=False, wait=True, retry_attempts=10, sleeping_time=360):
        """Binds an org. Stores the status of an org as a lightweight tag in Github"""
        tagname = self._get_tagname(orgname, sandbox)

        current_tags = self._get_tags(tagname)
        if len(current_tags) > 0:
            if wait is False:
                raise OrgBoundException('Org ' + orgname + ' already bound. Either the org is in use by another build or you '
                                                           'did not release the org')
            else:
                if retry_attempts > 0:
                    time.sleep(sleeping_time)
                    self.bind_org(orgname, sandbox=sandbox, wait=wait, retry_attempts=retry_attempts-1,
                                  sleeping_time=sleeping_time)
                else:
                    raise OrgBoundException('Org ' + orgname + ' bound too long. Either the org is in use by another '
                                                               'long-running build or you '
                                                               'did not release the org.')
        else:
            self._set_tag_in_repo(tagname)
            os.environ["BOUND_ORG_NAME"] = tagname

    def _get_tags(self, start_label=None):
        refs = self._repo.get_git_refs()
        if start_label:
            f = lambda ref: ref.ref.startswith("refs/tags/" + urllib.quote_plus(
                start_label))
        else:
            f = lambda ref: ref.ref.startswith("refs/tags/")
        tags = filter(f, refs)
        return tags

    def _get_tagname(self, orgname, sandbox):
        if sandbox:
            orgname += '.test'
        return orgname

    def _set_tag_in_repo(self, tagname):
        tagref = 'refs/tags/' + urllib.quote_plus(tagname)
        tag = self._repo.create_git_ref(tagref, self._sha)
        return tag

    def release_org(self, orgname, sandbox=False):
        tagname = self._get_tagname(orgname, sandbox)

        current_tags = self._get_tags(tagname)

        if len(current_tags) == 1:
            tag = current_tags[0]
            tag.delete()
        elif len(current_tags) == 0:
            raise OrgBoundException('Orgname ' + orgname + ' not bound. Sandbox mode: ' + str(sandbox))
        else:
            raise OrgBoundException('Orgname ' + orgname + ' multiple times bound! Sandbox mode: ' + str(sandbox))


def bind_org(orgname, storage_configuration, sandbox=False, wait=True, retry_attempts=10, sleeping_time=60):
    """Binds an org with the given orgname"""

    storage = _get_storage(storage_configuration)

    storage.bind_org(orgname, sandbox, wait, retry_attempts, sleeping_time)


def release_org(orgname, storage_configuration, sandbox=False):
    """Releases an org so it can be used in another process"""

    storage = _get_storage(storage_configuration)

    storage.release_org(orgname, sandbox)


def _get_storage(storage_configuration):
    if storage_configuration['GITHUB_USERNAME'] is not None:
        return GithubTagStorage(storage_configuration)
    else:
        raise OrgBoundException('Unknown storage configuration')






