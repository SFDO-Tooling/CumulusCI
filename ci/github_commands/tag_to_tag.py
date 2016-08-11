import os
import sys
from github import Github
from github.GithubException import GithubException

def tag_to_tag():
    SRC_TAG=os.environ.get('SRC_TAG')
    ORG_NAME=os.environ.get('GITHUB_ORG_NAME')
    REPO_NAME=os.environ.get('GITHUB_REPO_NAME')
    USERNAME=os.environ.get('GITHUB_USERNAME')
    PASSWORD=os.environ.get('GITHUB_PASSWORD')
    TAG=os.environ.get('TAG')
    
    print 'Attempting to create tag %s from tag %s' % (TAG, SRC_TAG)
    
    g = Github(USERNAME,PASSWORD)
    
    org = g.get_organization(ORG_NAME)
    repo = org.get_repo(REPO_NAME)
    
    # Get the source tag by name, error if none found
    src_tag = None
    for tag in repo.get_tags():
        print tag.name
        if tag.name == SRC_TAG:
            src_tag = tag
            break
    if not src_tag:
        print 'No tag named %s found' % SRC_TAG
        exit(1)
    
    tag = repo.create_git_tag(TAG, 'Created from tag %s' % SRC_TAG, src_tag.commit.sha, 'commit')
    print 'Tag Created:'
    print tag._rawData
    
    # Could not figure out how to look up the existing but decided against it
    # anyhow as Jenkins shouldn't be rewriting git tags automatically.  If a tag
    # needs to be overwritten, it must first be manually deleted
    # Delete the existing ref
    #existing_ref = repo.get_git_ref('tag/%s' % TAG)
    #if existing_ref:
    #    print 'Existing ref found, deleting it to set new one'
    #    existing_ref.delete()
    
    ref = repo.create_git_ref('refs/tags/%s' % TAG, tag.sha)
    print 'Ref Created:'
    print ref._rawData
    
    print 'SUCCESS'

if __name__ == '__main__':
    try:
        tag_to_tag()
    except:
        import traceback
        exc_type, exc_value, exc_traceback = sys.exc_info()
        print '-'*60
        traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stdout)
        print '-'*60
        sys.exit(1)
