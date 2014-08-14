import os
import requests
import json
import datetime
import re
from github import Github
from distutils.version import LooseVersion
from subprocess import call

ORG_NAME=os.environ.get('ORG_NAME')
REPO_NAME=os.environ.get('REPO_NAME')
USERNAME=os.environ.get('USERNAME')
PASSWORD=os.environ.get('PASSWORD')
MASTER_BRANCH=os.environ.get('MASTER_BRANCH')
LAST_REL_TAG=os.environ.get('LAST_REL_TAG')
CURRENT_REL_TAG=os.environ.get('CURRENT_REL_TAG')

gh = Github(USERNAME, PASSWORD)
org = gh.get_organization(ORG_NAME)
repo = org.get_repo(REPO_NAME)
 
# custom api wrapper for release interaction
def call_api(subpath, data=None):
    """ Takes a subpath under the repository (ex: /releases) and returns the json data from the api """
    api_url = 'https://api.github.com/repos/%s/%s%s' % (ORG_NAME, REPO_NAME, subpath)
    # Use Github Authentication if available for the repo
    kwargs = {}
    if USERNAME and PASSWORD:
        kwargs['auth'] = (USERNAME, PASSWORD)

    if data:
        resp = requests.post(api_url, data=json.dumps(data), **kwargs)
    else:
        resp = requests.get(api_url, **kwargs)

    try:
        data = json.loads(resp.content)
        return data
    except:
        return resp.status_code

# If LAST_REL_TAG was not provided, find the last release tag and set it as LAST_REL_TAG
if not LAST_REL_TAG:
    if CURRENT_REL_TAG.startswith('rel/'):
        current_version = LooseVersion(CURRENT_REL_TAG.replace('rel/',''))
    else:
        current_version = LooseVersion(CURRENT_REL_TAG.replace('uat/',''))

    print 'LAST_REL_TAG not specified, finding last release tag'
    versions = []
    for tag in repo.get_tags():
        if re.search('rel/[0-9][0-9]*\.[0-9][0-9]*', tag.name):
            version = LooseVersion(tag.name.replace('rel/',''))
            # Skip the CURRENT_REL_TAG and any newer releases
            if version >= current_version:
                continue
            versions.append(version)
    versions.sort()
    versions.reverse()
    LAST_REL_TAG = 'rel/%s' % versions[0]
    print 'Found last release tag: %s' % LAST_REL_TAG

# Find the start and end date for pull requests by finding the commits from the tags
last_rel_ref = call_api('/git/refs/tags/%s' % LAST_REL_TAG)
if last_rel_ref['object']['type'] == 'tag':
    last_rel_tag = call_api('/git/tags/%s' % last_rel_ref['object']['sha'])
    last_rel_commit = call_api('/git/commits/%s' % last_rel_tag['object']['sha'])
else:
    last_rel_commit = call_api('/git/commits/%s' % last_rel_ref['object']['sha'])

current_rel_ref = call_api('/git/refs/tags/%s' % CURRENT_REL_TAG)
if current_rel_ref['object']['type'] == 'tag':
    current_rel_tag = call_api('/git/tags/%s' % current_rel_ref['object']['sha'])
    current_rel_commit = call_api('/git/commits/%s' % current_rel_tag['object']['sha'])
else:
    current_rel_commit = call_api('/git/commits/%s' % current_rel_ref['object']['sha'])

since_date = datetime.datetime.strptime(last_rel_commit['committer']['date'], "%Y-%m-%dT%H:%M:%SZ")
until_date = datetime.datetime.strptime(current_rel_commit['committer']['date'], "%Y-%m-%dT%H:%M:%SZ")

# Unfortunately, there is no ability to filter pull requests by date merged so we have to fetch all and loop through them
pulls = repo.get_pulls(state='closed')

pulls = []

for pull in repo.get_pulls(state='closed'):
    merged = pull.merged_at
    if not merged:
        continue
    if pull.base.ref != MASTER_BRANCH:
        continue
    if merged <= until_date and merged > since_date:
        pulls.append(pull)

content = {
    'warning': [],
    'info': [],
    'issues': [],
}

pulls.reverse()

for pull in pulls:
    section = None
    in_info = False
    in_issues = False
    for line in pull.body.split('\n'):
        if line.startswith('# Warning'):
            section = 'warning'
            continue
        if line.startswith('# Info'):
            section = 'info'
            continue
        if line.startswith('# Issues'):
            section = 'issues'
            continue

        # Ignore everything at the top of the pull request body until we hit a heading we care about
        if not section:
            continue

        # Skip empty lines
        line = line.strip()
        if not line:
            continue

        # If we got here, we are in a section and want to extract the line as content
        if section == 'issues':
            # Parse out the issue number as int
            issue = re.sub(r'^[F|f]ix.* #([0-9][0-9]*).*$', r'\1', line)
            if issue:
                issue = int(issue)
                if issue not in content[section]:
                    content[section].append(issue)
        else:
            content[section].append(line)

# If there is no content found, exit
if not content['warning'] and not content['info'] and not content['issues']:
    print 'No release note content found, exiting'
    exit()

# Sort issues by issue number
content['issues'].sort()

f = open('release_notes.md', 'w')

if content['warning']:
    f.write('# Critical Changes\r\n')
    for line in content['warning']:
        f.write('%s\r\n' % line)
    if content['info'] or content['issues']:
        f.write('\r\n')
if content['info']:
    f.write('# Changes\r\n')
    for line in content['info']:
        f.write('%s\r\n' % line)
    if content['issues']:
        f.write('\r\n')
if content['issues']:
    f.write('# Issues Closed\r\n')
    for issue in content['issues']:
        # Get the issue title to include
        gh_issue = call_api('/issues/%s' % issue)
        f.write('#%s: %s\r\n' % (issue, gh_issue['title']))

f.close()

f = open('release_notes.md', 'r')
release_notes = f.read()
f.close()

print '----- RELEASE NOTES -----'
print release_notes
print '----- END RELEASE NOTES -----'

# Add the release notes to the body of the release
releases = call_api('/releases')
for release in releases:
    if release['tag_name'] == CURRENT_REL_TAG:
        print 'Adding release notes to body of %s' % release['html_url']

        data = {
            "tag_name": release['tag_name'],
            "target_commitish": release['target_commitish'],
            "name": release['name'],
            "body": release['body'], 
            "draft": release['draft'],
            "prerelease": release['prerelease'],
        }

        if data['body']:
            data['body'] += '\r\n%s' % release_notes
        else:
            data['body'] = release_notes

        call_api('/releases/%s' % release['id'], data=data)
        break
