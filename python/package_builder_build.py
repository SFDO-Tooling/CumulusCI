import json
import os
import requests
from time import sleep
from urllib import quote

BUILDER_URL=os.environ.get('BUILDER_URL')
BUILDER_KEY=os.environ.get('BUILDER_KEY')
BUILD_NAME=os.environ.get('BUILD_NAME')
BUILD_NAME=os.environ.get('BUILD_NAME')
BUILD_COMMIT=os.environ.get('BUILD_COMMIT')
BUILD_WORKSPACE=os.environ.get('BUILD_WORKSPACE')

resp = requests.get('%s/build?name=%s&revision=%s' % (BUILDER_URL, quote(BUILD_NAME), quote(BUILD_COMMIT)), headers={'Authorization': BUILDER_KEY}, verify=False)
status_url = '%s?format=json' % resp.url

last_message = None
while True:
    resp = requests.get(status_url, verify=False)
    data = json.loads(resp.content)

    if data['status'] == 'Complete':
        print 'Build Complete'
        print '-------------------'
        print 'Version: %s' % data['version']
        print 'Install URL: %s' % data['install_url']
        print 'Writing package.properties file'
        f = open('%s/package.properties' % BUILD_WORKSPACE, 'w')
        f.write('PACKAGE_VERSION=%s\n' % data['version'])
        f.write('INSTALL_URL=%s\n' % data['install_url'])
        f.write('BUILD_COMMIT=%s\n' % data['revision'])
        f.close()
        break

    if data['status'] == 'Failed':
        print 'Build Failed'
        print '-------------------'
        print 'Message: %s' % data['message']
        exit(1)

    # Print the message if it has changed
    if last_message != data['message']:
        print '%s: %s' % (data['status'],data['message'])

    last_message = data['message']
    sleep(5)
