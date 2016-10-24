import os
import sys
import csv
from push_api import SalesforcePushApi

# Force UTF8 output
reload(sys)
sys.setdefaultencoding('UTF8')

if __name__ == '__main__':
    try:
        
        username = os.environ.get('SF_USERNAME')
        password = os.environ.get('SF_PASSWORD')
        serverurl = os.environ.get('SF_SERVERURL')
        namespace = os.environ.get('NAMESPACE')
        version = os.environ.get('VERSION_NUMBER')

        # Parse the version number string
        major = None
        minor = None
        patch = None
        build = None
        state = 'Released'
        version_parts = version.split('.')
        if len(version_parts) >= 1:
            major = version_parts[0]
        if len(version_parts) == 2:
            minor = version_parts[1]
            if minor.find('Beta') != -1:
                state = 'Beta'
                minor, build = minor.replace(' (Beta ',',').replace(')','').split(',')
        if len(version_parts) > 2:
            minor = version_parts[1]
            patch = version_parts[2]
            if patch.find('Beta') != -1:
                state = 'Beta'
                patch, build = minor.replace(' (Beta ',',').replace(')','').split(',')

        push_api = SalesforcePushApi(username, password, serverurl)
        package = push_api.get_package_objs("NamespacePrefix = '%s'" % namespace, limit=1)[0]

        version_where = "ReleaseState = '%s' AND MajorVersion = %s AND MinorVersion = %s" % (state, major, minor)
        if patch:
             version_where += " AND PatchVersion = %s" % patch
        if state == 'Beta' and build:
             version_where += " AND BuildNumber = %s" % build

        version = push_api.get_package_version_objs(version_where, limit=1)[0]

        print version.sf_id

    except SystemExit:
        sys.exit(1)
    except:
        import traceback
        exc_type, exc_value, exc_traceback = sys.exc_info()
        print '-'*60
        traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stdout)
        print '-'*60
        sys.exit(2)
