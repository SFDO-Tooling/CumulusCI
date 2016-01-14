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
        push_request_id = os.environ.get('PUSH_REQUEST')
        subscriber_where = os.environ.get('SUBSCRIBER_WHERE', None)

        default_where = {'PackagePushRequest': "Id = '%s'" % push_request_id}
        if subscriber_where:
            default_where['PackageSubscriber'] = subscriber_where

        push_api = SalesforcePushApi(username, password, serverurl, lazy=['subscribers',], default_where=default_where)
        push_request = push_api.get_push_request_objs("Id = '%s'" % push_request_id, limit=1)[0]

        failing_orgs = []

        failing_jobs = push_request.get_push_job_objs("Status = 'Failed'")
        for job in failing_jobs:
            if job.org:
                failing_orgs.append(job.org.org_key)

        for org in failing_orgs:
            print org

    except SystemExit:
        sys.exit(1)            
    except:
        import traceback
        exc_type, exc_value, exc_traceback = sys.exc_info()
        print '-'*60
        traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stdout)
        print '-'*60
        sys.exit(2)
