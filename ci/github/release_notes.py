import os
import sys
import requests
import json
import datetime
import re
import codecs
from github import Github
from distutils.version import LooseVersion
from subprocess import call

ORG_NAME=os.environ.get('GITHUB_ORG_NAME')
REPO_NAME=os.environ.get('GITHUB_REPO_NAME')
USERNAME=os.environ.get('GITHUB_USERNAME')
PASSWORD=os.environ.get('GITHUB_PASSWORD')
MASTER_BRANCH=os.environ.get('MASTER_BRANCH')
LAST_REL_TAG=os.environ.get('LAST_REL_TAG', None)
CURRENT_REL_TAG=os.environ.get('CURRENT_REL_TAG')
PREFIX_BETA=os.environ.get('PREFIX_BETA', 'beta/')
PREFIX_RELEASE=os.environ.get('PREFIX_RELEASE', 'release/')
PRINT_ONLY=os.environ.get('PRINT_ONLY','') in ('true','True')
    
# custom api wrapper for release interaction
def call_api(subpath, data=None):
    """ Takes a subpath under the repository (ex: /releases) and returns the json data from the api """
    global ORG_NAME
    global REPO_NAME
    global USERNAME
    global PASSWORD
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


def create_release_notes():
    global ORG_NAME
    global REPO_NAME
    global USERNAME
    global PASSWORD
    global MASTER_BRANCH
    global LAST_REL_TAG
    global CURRENT_REL_TAG
    global PREFIX_BETA
    global PREFIX_RELEASE

    gh = Github(USERNAME, PASSWORD)
    try:
        org = gh.get_organization(ORG_NAME)
    except:
        org = gh.get_user(ORG_NAME)
    repo = org.get_repo(REPO_NAME)
    
    # If LAST_REL_TAG was not provided, find the last release tag and set it as LAST_REL_TAG
    if not LAST_REL_TAG:
        if CURRENT_REL_TAG.startswith(PREFIX_RELEASE):
            current_version = LooseVersion(CURRENT_REL_TAG.replace(PREFIX_RELEASE,''))
        else:
            current_version = LooseVersion(CURRENT_REL_TAG.replace(PREFIX_BETA,''))
    
        print 'LAST_REL_TAG not specified, finding last release tag'
        versions = []
        for tag in repo.get_tags():
            if re.search('%s[0-9][0-9]*\.[0-9][0-9]*' % PREFIX_RELEASE, tag.name):
                version = LooseVersion(tag.name.replace(PREFIX_RELEASE,''))
                # Skip the CURRENT_REL_TAG and any newer releases
                if version >= current_version:
                    continue
                versions.append(version)
        versions.sort()
        versions.reverse()
        if versions:
            LAST_REL_TAG = '%s%s' % (PREFIX_RELEASE, versions[0])
        print 'Found last release tag: %s' % LAST_REL_TAG
    
    # Find the start and end date for pull requests by finding the commits from the tags
    last_rel_commit = None
    if LAST_REL_TAG:
        last_rel_ref = call_api('/git/refs/tags/%s' % LAST_REL_TAG)
        if last_rel_ref['object']['type'] == 'tag':
            last_rel_tag = call_api('/git/tags/%s' % last_rel_ref['object']['sha'])
            last_rel_commit = call_api('/git/commits/%s' % last_rel_tag['object']['sha'])
        else:
            last_rel_commit = call_api('/git/commits/%s' % last_rel_ref['object']['sha'])

    current_rel_ref = call_api('/git/refs/tags/%s' % CURRENT_REL_TAG)
    print current_rel_ref
    if current_rel_ref['object']['type'] == 'tag':
        current_rel_tag = call_api('/git/tags/%s' % current_rel_ref['object']['sha'])
        current_rel_commit = call_api('/git/commits/%s' % current_rel_tag['object']['sha'])
    else:
        current_rel_commit = call_api('/git/commits/%s' % current_rel_ref['object']['sha'])
    
    if last_rel_commit:
        since_date = datetime.datetime.strptime(last_rel_commit['committer']['date'], "%Y-%m-%dT%H:%M:%SZ")
    else:
        since_date = datetime.datetime(1999, 1, 1)

    until_date = datetime.datetime.strptime(current_rel_commit['committer']['date'], "%Y-%m-%dT%H:%M:%SZ")
    
    # Get the released package version number
    if CURRENT_REL_TAG.startswith(PREFIX_RELEASE):
        release_version = CURRENT_REL_TAG.replace(PREFIX_RELEASE,'')
    else:
        release_version = '%s)' % CURRENT_REL_TAG.replace(PREFIX_BETA,'').replace('-', ' (').replace('Beta_', 'Beta ')
    
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
    
            # Skip empty lines and trim extra spaces from line end
            line = line.rstrip()
            if not line.strip():
                continue
    
            # If we got here, we are in a section and want to extract the line as content
            if section == 'issues':
                # Parse out the issue number as int
                issue = re.sub(r'.*[F|f]ix.* #([0-9][0-9]*).*$', r'\1', line)
                if issue:
                    issue = int(issue)
                    if issue not in content[section]:
                        content[section].append(issue)
            else:
                content[section].append(line)
    
    # If there is no content found, exit
    if not content['warning'] and not content['info'] and not content['issues']:
        print 'No release note content found, exiting'
        return
    
    # Sort issues by issue number
    content['issues'].sort()
    
    f = codecs.open('release_notes.md', encoding='utf-8', mode='w')
    
    if content['warning']:
        f.write(u'# Critical Changes\r\n')
        for line in content['warning']:
            f.write(u'{0}\r\n'.format(line,))
        if content['info'] or content['issues']:
            f.write(u'\r\n')
    if content['info']:
        f.write(u'# Changes\r\n')
        for line in content['info']:
            f.write(u'{0}\r\n'.format(line,))
        if content['issues']:
            f.write(u'\r\n')
    if content['issues']:
        f.write(u'# Issues Closed\r\n')
        for issue in content['issues']:
            # Get the issue title to include
            gh_issue = call_api('/issues/%s' % issue)
            f.write(u'#{0}: {1}\r\n'.format(issue, gh_issue['title']))
    
            # Ensure all issues have a comment on which release they were fixed
            gh_issue_comments = call_api('/issues/%s/comments' % issue)
            has_comment = False
            for comment in gh_issue_comments:
                if CURRENT_REL_TAG.startswith(PREFIX_RELEASE):
                    if comment['body'].find('Included in production release') != -1:
                        has_comment = True
                else:
                    if comment['body'].find('Included in beta release') != -1:
                        has_comment = True
            if not has_comment:
                if CURRENT_REL_TAG.startswith(PREFIX_RELEASE):
                    data = {'body': 'Included in production release version %s' % release_version}
                    print "Adding comment on issue #%s with the production release version" % issue
                else:
                    data = {'body': 'Included in beta release version %s and higher' % release_version}
                    print "Adding comment on issue #%s with the beta release version" % issue
                call_api('/issues/%s/comments' % issue, data=data)
    
    f.close()
    
    f = codecs.open('release_notes.md', encoding='utf-8', mode='r')
    release_notes = f.read()
    f.close()
    
    print '----- RELEASE NOTES -----'
    print release_notes.encode('utf-8')
    print '----- END RELEASE NOTES -----'
    
    # Add the release notes to the body of the release
    if not PRINT_ONLY:
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
                    new_body = {
                        'pre': [],
                        'post': [],
                    }
                    found_release_notes = False
                    in_release_notes = False
                    
                    for line in data['body'].split('\n'):
                        if line.startswith(('# Critical Changes', '# Changes', '# Issues Closed')):
                            found_release_notes = True
                            in_release_notes = True
                       
                        # Skip empty lines 
                        elif not line.strip():
                            in_release_notes = False
                            continue

                        if not in_release_notes:
                            if found_release_notes:
                                new_body['post'].append(line)
                            else:
                                new_body['pre'].append(line)
                            
                    data['body'] = u'{0}\r\n{1}\r\n{2}'.format(
                        '\r\n'.join(new_body['pre']), 
                        release_notes, 
                        '\r\n'.join(new_body['post']),
                    )
                else:
                    data['body'] = release_notes
        
                call_api('/releases/%s' % release['id'], data=data)
                break

if __name__ == '__main__':
    try:
        create_release_notes()
    except:
        import traceback
        exc_type, exc_value, exc_traceback = sys.exc_info()
        print '-'*60
        traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stdout)
        print '-'*60
        sys.exit(1)
