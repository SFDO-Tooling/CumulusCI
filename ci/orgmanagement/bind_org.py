import time

from github_commands.get_tags import get_tags
from github_commands.set_tag import set_tag

SLEEP_PERIOD_IN_SECONDS = 60


class OrgBoundException(Exception):
    pass


#TODO should stop passing around github user details. Pass around the github object/repo
def bind_org(orgname, sha, github_organization, github_user, github_password,
             github_repository, fail=True, sandbox=False, retry_attempts=10, sleeping_time=60):

    assert type(orgname) is str
    assert type(sha) is str
    assert type(github_organization) is str
    assert type(github_user) is str
    assert type(github_password) is str
    assert type(github_repository) is str

    tagname = _get_tagname(orgname, sandbox)
    current_tags = get_tags(github_organization, github_repository, github_user, github_password, tagname)

    if len(current_tags) > 0:
        if fail is True:
            raise OrgBoundException('Org ' + orgname + ' already bound. Either the org is in use by another build or you '
                                                   'did not release the org')
        else:
            if retry_attempts > 0:
                time.sleep(SLEEP_PERIOD_IN_SECONDS)
                bind_org(orgname, sha, github_organization, github_user, github_password, github_repository,
                         fail=fail, sandbox=sandbox, retry_attempts=retry_attempts-1, sleeping_time=sleeping_time)
            else:
                raise OrgBoundException('Org ' + orgname + ' bound too long. Either the org is in use by another '
                                                           'long-running build or you '
                                                           'did not release the org.')
    else:
        set_tag(github_organization, github_repository, github_user, github_password, tagname, sha)


def _get_tagname(orgname, sandbox):
    if sandbox:
        orgname += '.test'
    return orgname



