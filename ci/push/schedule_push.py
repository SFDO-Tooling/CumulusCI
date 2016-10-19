import os
import sys
import csv
import time
from push_api import SalesforcePushApi
from datetime import datetime
from datetime import timedelta

# Force UTF8 output
reload(sys)
sys.setdefaultencoding('UTF8')

if __name__ == '__main__':
    try:

        username = os.environ.get('SF_USERNAME')
        password = os.environ.get('SF_PASSWORD')
        serverurl = os.environ.get('SF_SERVERURL')
        version = os.environ.get('VERSION')
        subscribers = os.environ.get('SUBSCRIBERS', None)
        subscribers_file = os.environ.get('SUBSCRIBERS_FILE', None)
        startTimeRaw = os.environ.get('START_TIME')

        if startTimeRaw:
            startTime = datetime.strptime(startTimeRaw, "%Y-%m-%dT%H:%M") # Example: 2016-10-19T10:00
        else:
            startTime = None

        if not subscribers and not subscribers_file:
            raise ValueError('You must provide either the SUBSCRIBERS or SUBSCRIBERS_FILE environment variables')

        if subscribers:
            orgs = subscribers.split(',')
        else:
            f_orgs = open(subscribers_file, 'r')
            orgs = []
            for org in f_orgs:
                orgs.append(org.strip())

        push_api = SalesforcePushApi(username, password, serverurl)
        version = push_api.get_package_version_objs("Id = '%s'" % version, limit=1)[0]
        print 'Scheduling push upgrade for %s.%s to %s orgs' % (version.major, version.minor, len(orgs))

        if startTime:
            print 'Scheduled start time: %s UTC' % startTime

        request_id = push_api.create_push_request(version, orgs, startTime)

        if len(orgs) > 1000:
            print "Delaying 30 seconds to allow all jobs to initialize..."
            time.sleep(30)

        print 'Push Request %s is populated, setting status to Pending to queue execution.' % request_id
        print push_api.run_push_request(request_id)

        print 'Push Request %s is queued for execution.' % request_id
    except SystemExit:
        sys.exit(1)
    except:
        import traceback
        exc_type, exc_value, exc_traceback = sys.exc_info()
        print '-'*60
        traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stdout)
        print '-'*60
        sys.exit(2)
