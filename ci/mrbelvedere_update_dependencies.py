import json
import os
import requests

MRBELVEDERE_BASE_URL=os.environ.get('MRBELVEDERE_BASE_URL')
PACKAGE_KEY=os.environ.get('MRBELVEDERE_PACKAGE_KEY')
NAMESPACE=os.environ.get('NAMESPACE')
BETA=os.environ.get('BETA', False)
VERSION=os.environ.get('PACKAGE_VERSION')
PROPERTIES_PATH=os.environ.get('PROPERTIES_PATH', None)

dependencies_url = '%s/%s/dependencies' % (MPINSTALLER_BASE_URL, NAMESPACE)
if BETA in ('True','true'):
    dependencies_url = dependencies_url + '/beta'

current_dependencies = json.loads(requests.get(dependencies_url).content)
dependencies = []

if PROPERTIES_PATH:
    f = open(PROPERTIES_PATH, 'r')
    for line in f.readlines():
        namespace, version = [x.strip() for x in line.split('=')]
        namespace = namespace.replace('version.','')
        # Skip any namespace with "Not Installed" as a the version
        if version == 'Not Installed':
            continue
        dependencies.append({'namespace': namespace, 'number': version})

dependencies.append({'namespace': NAMESPACE, 'number': VERSION})

changed = False
for package in current_dependencies:
    matched = False
    for new in dependencies:
        if new['namespace'] == package['namespace']:
            matched = True
            if new['number'] == package['number']:
                print "No change for %s" % new['namespace']
            else:
                print "Changing %s from %s to %s" % (package['namespace'], package['number'], new['number'])
                changed = True
            break
    if not matched:
        print "No change for %s" % package['namespace']  

if changed:
    resp = requests.post(dependencies_url, data=json.dumps(dependencies), headers={'Authorization': PACKAGE_KEY})
