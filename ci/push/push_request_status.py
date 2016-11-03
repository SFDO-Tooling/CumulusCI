import os
import sys
import csv
import time
from push_api import SalesforcePushApi

# Force UTF8 output
reload(sys)
sys.setdefaultencoding('UTF8')

completed_statuses = ['Succeeded','Failed','Cancelled']

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

        push_api = SalesforcePushApi(username, password, serverurl, lazy=['subscribers','jobs'], default_where=default_where)
        push_request = push_api.get_push_request_objs("Id = '%s'" % push_request_id, limit=1)[0]

        interval = 10
        if push_request.status not in completed_statuses:
            print 'Push request is not yet complete.  Polling for status every %s seconds until completion...' % interval
            sys.stdout.flush()

        i = 0
        while push_request.status not in completed_statuses:
            if i == 10:
                print 'This is taking a while! Polling every 60 seconds...'
                sys.stdout.flush()
                interval = 60
            time.sleep(interval)
    
            # Clear the method level cache on get_push_requests and get_push_request_objs
            push_api.get_push_requests.cache.clear()
            push_api.get_push_request_objs.cache.clear()

            # Get the push_request again
            push_request = push_api.get_push_request_objs("Id = '%s'" % push_request_id, limit=1)[0]

            print push_request.status
            sys.stdout.flush()
            
            i += 1


        failed_jobs = []
        success_jobs = []
        cancelled_jobs = []

        jobs = push_request.get_push_job_objs()
        for job in jobs:
            if job.status == 'Failed':
                failed_jobs.append(job)
            elif job.status == 'Succeeded':
                success_jobs.append(job)
            elif job.status == 'Cancelled':
                cancelled_jobs.append(job)

        print "Push complete: %s succeeded, %s failed, %s cancelled" % (len(success_jobs),len(failed_jobs),len(cancelled_jobs))
        sys.stdout.flush()

        failed_by_error = {}
        for job in failed_jobs:
            errors = job.get_push_error_objs()
            for error in errors:
                error_key = (error.error_type, error.title, error.message, error.details)
                if error_key not in failed_by_error:
                    failed_by_error[error_key] = []
                failed_by_error[error_key].append(error)

        if failed_jobs:
            print ""
            print "-----------------------------------"
            print "Failures by error type"
            print "-----------------------------------"
            sys.stdout.flush()
            for key, errors in failed_by_error.items():
                print "    "
                print "%s failed with..." % (len(errors))
                print "    Error Type = %s" % key[0]
                print "    Title = %s" % key[1]
                print "    Message = %s" % key[2]
                print "    Details = %s" % key[3]
                sys.stdout.flush()
        

    except SystemExit:
        sys.exit(1)            
    except:
        import traceback
        exc_type, exc_value, exc_traceback = sys.exc_info()
        print '-'*60
        traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stdout)
        print '-'*60
        sys.exit(2)
