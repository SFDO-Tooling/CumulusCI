import argparse
import os
import sys
from github3 import login

class HasOpenPull(object):

    def __init__(self):
        self._init_github()

    def _init_github(self):
        username = os.environ.get('GITHUB_USERNAME')
        password = os.environ.get('GITHUB_PASSWORD')
        if not username or not password:
            print "Could not find Github username and password from the environment variables GITHUB_USERNAME and GITHUB_PASSWORD"
            sys.exit(1)
        self.gh = login(username, password)
        self.repo = self.gh.repository(
            'SalesforceFoundation',
            'CumulusCI',
        )
   
    def __call__(self, branch): 
        for pull in self.repo.iter_pulls(state='open', base='master'):
            if pull.head.ref == branch:
                return pull

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Check if a branch has an open pull request in Github')
    parser.add_argument('branch', type=str, help='The branch name to check')
    args = parser.parse_args()
    has_open_pull = HasOpenPull()
    pr = has_open_pull(args.branch)
    if pr:
        print "#{}".format(pr.number)
