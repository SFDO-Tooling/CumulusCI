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
        request_id = os.environ.get('PUSH_REQUEST')
        status = os.environ.get('PUSH_REQUEST_STATUS')

        push_api = SalesforcePushApi(username, password, serverurl)
        request = push_api.get_push_request_objs("Id = '%s'" % request_id, limit=1)[0]
        if request.status != status:
            print 'Updating status for Push Request %s from %s to %s' % (request_id, request.status, status)
            print push_api.sf.PackagePushRequest.update(request_id, {'Status': status})
        else:
            print 'Status for Push Request %s is already %s' % (request_id, status)

    except SystemExit:
        sys.exit(1)
    except:
        import traceback
        exc_type, exc_value, exc_traceback = sys.exc_info()
        print '-'*60
        traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stdout)
        print '-'*60
        sys.exit(2)
