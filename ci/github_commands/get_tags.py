import os
import sys
import github


def get_tags(org_name, repo_name, username, password, start_label=None):
    """returns all the tags in a certain repo filtered on start_label"""
    g = login_github(username, password)
    org = get_github_organization(g, org_name, repo_name)
    repo = org.get_repo(repo_name)
    tags = get_tags_from_repo(repo, start_label)
    return tags


def login_github(username, password):
    return github.Github(username, password)


def get_github_organization(gh, org_name):
    try:
        org = gh.get_organization(org_name)
    except:
        org = gh.get_user(org_name)
    return org


def get_tags_from_repo(repo, start_label=None):
    refs = repo.get_git_refs()
    if start_label:
        f = lambda ref: (ref.object.type == "tag") & (ref.ref.startswith("refs/tags/" + start_label))
    else:
        f = lambda ref: (ref.object.type == "tag")
    tags = filter(f, refs)
    return tags

if __name__ == '__main__':
    try:
        ORG_NAME=os.environ.get('GITHUB_ORG_NAME')
        REPO_NAME=os.environ.get('GITHUB_REPO_NAME')
        USERNAME=os.environ.get('GITHUB_USERNAME')
        PASSWORD=os.environ.get('GITHUB_PASSWORD')
        get_tags(ORG_NAME, REPO_NAME, USERNAME, PASSWORD)
    except:
        import traceback
        exc_type, exc_value, exc_traceback = sys.exc_info()
        print '-'*60
        traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stdout)
        print '-'*60
        sys.exit(1)
