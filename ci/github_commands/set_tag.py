import github
import urllib


def set_tag(org_name, repo_name, username, password, tagname, sha):
    """returns all the tags in a certain repo filtered on start_label"""
    # TODO: refactor set_tag and get_tags so they reuse one Github access class
    g = login_github(username, password)
    org = get_github_organization(g, org_name)
    repo = org.get_repo(repo_name)
    tag = set_tag_in_repo(repo, tagname, sha)
    return tag


def login_github(username, password):
    return github.Github(username, password)


def get_github_organization(gh, org_name):
    try:
        org = gh.get_organization(org_name)
    except:
        org = gh.get_user(org_name)
    return org

def set_tag_in_repo(repo, tagname, sha):
    tagref = '/tags/' + urllib.quote_plus(tagname)
    tag = repo.create_git_ref(tagref, sha)
    return tag


