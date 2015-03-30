import os
import sys
from github import Github
from github.GithubException import GithubException

def merge_master_to_feature():
    ORG_NAME=os.environ.get('GITHUB_ORG_NAME')
    REPO_NAME=os.environ.get('GITHUB_REPO_NAME')
    MASTER_BRANCH=os.environ.get('MASTER_BRANCH','master')
    USERNAME=os.environ.get('GITHUB_USERNAME')
    PASSWORD=os.environ.get('GITHUB_PASSWORD')
    BUILD_COMMIT=os.environ.get('BUILD_COMMIT', None)
    
    g = Github(USERNAME,PASSWORD)

    try:
        org = g.get_organization(ORG_NAME)
    except:
        org = g.get_user(ORG_NAME)
    repo = org.get_repo(REPO_NAME)
    
    master = repo.get_branch(MASTER_BRANCH)
    
    exception = None
    
    pulls = repo.get_pulls()
    
    for branch in repo.get_branches():
        # Skip any branches which don't start with feature/
        if not branch.name.startswith('feature/'):
            print 'Skipping branch %s: does not start with feature/' % branch.name
            continue
    
        # Skip the master branch
        if branch.name == master.name:
            print 'Skipping branch %s: is master branch' % branch.name
            continue
    
        # Skip branches which are not behind dev
        # Changed to check if the files list is empty since merge creates a new commit on dev
        # which makes the merged feature branch behind by a commit but with no files.
    
        # Get a comparison of master vs branch.  compare.ahead_by means master is head of the branch.
        # This orientation is necessary so the compare.files list lists files changed in master but not
        # in the branch.
        if BUILD_COMMIT:
            compare = repo.compare(branch.commit.sha, BUILD_COMMIT)
        else:
            compare = repo.compare(branch.commit.sha, master.commit.sha)
        if not compare.files:
            print 'Skipping branch %s: branch has no files different than %s' % (branch.name, master.name)
            continue
    
        # Try to do a merge directly in Github
        try:
            merge = repo.merge(branch.name, master.name)
            print 'Merged %s commits into %s (%s)' % (compare.ahead_by, branch.name, merge.sha)
        except GithubException, e:
            # Auto-merge failed
            if e.data.get('message') == u'Merge conflict':
                existing_pull = None
                for pull in pulls:
                    if pull.base.ref == branch.name:
                        existing_pull = pull
                        print 'Skipping branch %s: pull request already exists' % branch.name
    
                if not existing_pull:
                    # If the failure was due to merge conflict, create a pull request
                    pull = repo.create_pull(
                        title="Merge conflict merging %s into %s" % (master.name, branch.name),
                        body="mrbelvedere tried to merge new commits to %s but hit a merge conflict.  Please resolve manually" % master.name,
                        base=branch.name,
                        head=master.name,
                    )
                    print 'Create pull request %s to resolve merge conflict in %s' % (pull.number, branch.name)
    
                    # Assign pull request to branch committers
                    commits = repo.get_commits(sha = branch.commit.sha)
                    assignee = None
                    # Find the most recent committer who is not the user used by this script
                    # NOTE: This presumes the user being used by this script is a robot user, not a real dev
                    for commit in commits:
                        try:
                            # Sometimes commit.committer.login does not exist in the response.  If so, continue 
                            if commit.committer.login != USERNAME:
                                assignee = commit.committer
                                break
                        except AttributeError:
                            pass
    
                    if assignee:
                        repo.get_issue(pull.number).edit(assignee = assignee)
    
            else:
                # For other types of failures, store the last exception and raise at the end
                exception = e
    
    if exception:
        # If an exception other than a merge conflict was encountered, raise it
        raise exception

if __name__ == '__main__':
    try:
        merge_master_to_feature()
    except:
        import traceback
        exc_type, exc_value, exc_traceback = sys.exc_info()
        print '-'*60
        traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stdout)
        print '-'*60
        sys.exit(1)
