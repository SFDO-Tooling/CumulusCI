import os
import requests
import json
from subprocess import call

ORG_NAME=os.environ.get('ORG_NAME')
REPO_NAME=os.environ.get('REPO_NAME')
USERNAME=os.environ.get('USERNAME')
PASSWORD=os.environ.get('PASSWORD')
BUILD_COMMIT=os.environ.get('BUILD_COMMIT')
INSTALL_URL=os.environ.get('INSTALL_URL')
PACKAGE_VERSION=os.environ.get('PACKAGE_VERSION')

def call_api(owner, repo, subpath, data=None, username=None, password=None):
    """ Takes a subpath under the repository (ex: /releases) and returns the json data from the api """
    api_url = 'https://api.github.com/repos/%s/%s%s' % (owner, repo, subpath)
    # Use Github Authentication if available for the repo
    kwargs = {}
    if username and password:
        kwargs['auth'] = (username, password)

    if data:
        resp = requests.post(api_url, data=json.dumps(data), **kwargs)
    else:
        resp = requests.get(api_url, **kwargs)

    try:
        data = json.loads(resp.content)
        return data
    except:
        return resp.status_code

existing = None

releases = call_api(ORG_NAME, REPO_NAME, '/releases', username=USERNAME, password=PASSWORD)
for rel in releases:
    if rel['name'] == PACKAGE_VERSION:
        existing = rel
        break

if existing:
    print 'Release for %s already exists' % PACKAGE_VERSION
    exit()

tag_name = PACKAGE_VERSION.replace(' (','-').replace(')','').replace(' ','_')

data = {
    'tag_name': 'uat/%s' % tag_name,
    'target_commitish': BUILD_COMMIT,
    'name': PACKAGE_VERSION,
    'body': INSTALL_URL,
    'draft': False,
    'prerelease': True,
}

rel = call_api(ORG_NAME, REPO_NAME, '/releases', data=data, username=USERNAME, password=PASSWORD)

print 'Release created:'
print rel

# Now, zip and upload the unpackaged directory

