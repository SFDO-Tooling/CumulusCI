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
        version = os.environ.get('VERSION')
        subscriber_where = os.environ.get('SUBSCRIBER_WHERE')

        default_where = {}
        if subscriber_where:
            default_where['PackageSubscriber'] = subscriber_where

        push_api = SalesforcePushApi(username, password, serverurl, lazy=['jobs','subscribers',], default_where=default_where)
        failing_subscribers = push_api.get_subscriber_objs("OrgStatus = 'Active' AND MetadataPackageVersionId != '%s'" % version)

        failing = {}
        for subscriber in failing_subscribers:

            # Get last successful push job (this is convoluted because I can't figure out how to use ORDER BY and LIMIT to only capture the one I want via SOQL)
            jobs_success = subscriber.get_push_job_objs("Status = 'Succeeded'")
            last_success = None
            for job in jobs_success:
                if not last_success or last_success.request.start_time < job.request.start_time:
                    last_success = job

            # Get last failed push job
            jobs_failed = subscriber.get_push_job_objs("Status = 'Failed'")
            last_failed = None
            for job in jobs_failed:
                if not last_failed or last_failed.request.start_time < job.request.start_time:
                    last_failed = job

            last_error = None
            if last_failed:
                last_error = last_failed.get_push_error_objs(limit=1)
                if last_error:
                    last_error = last_error[0]

            failing[subscriber.org_key] = {
                'org_id': subscriber.org_key,
                'org_name': subscriber.org_name,
                'org_version': subscriber.version.version_number,
                'org_type': subscriber.org_type,
                'org_status': subscriber.org_status,
                'install_status': subscriber.status,
                'last_success_date': None,
                'last_success_version': None,
                'last_failed_date': None,
                'last_failed_version': None,
                'last_failed_severity': None,
                'last_failed_error_type': None,
                'last_failed_title': None,
                'last_failed_message': None,
                'last_failed_details': None,
            }
            if last_success:
                failing[subscriber.org_key]['last_success_date'] = last_success.request.start_time
                failing[subscriber.org_key]['last_success_version'] = last_success.request.version.version_number
            if last_failed:
                failing[subscriber.org_key]['last_failed_date'] = last_failed.request.start_time
                failing[subscriber.org_key]['last_failed_version'] = last_failed.request.version.version_number
            if last_error:
                failing[subscriber.org_key]['last_failed_severity'] = last_error.severity
                failing[subscriber.org_key]['last_failed_error_type'] = last_error.error_type
                failing[subscriber.org_key]['last_failed_title'] = last_error.title
                failing[subscriber.org_key]['last_failed_message'] = last_error.message
                failing[subscriber.org_key]['last_failed_details'] = last_error.details

        csv_file = open('failing_orgs.csv','w')
        fieldnames = ('org_id','org_name','org_version','org_type','org_status','install_status','last_success_date','last_success_version','last_failed_date','last_failed_version','last_failed_severity','last_failed_error_type','last_failed_title','last_failed_message','last_failed_details')
        csv_writer = csv.DictWriter(csv_file, delimiter=',', fieldnames=fieldnames)
        csv_writer.writerow(dict((fn,fn) for fn in fieldnames))
        for row in failing.values():
            csv_writer.writerow(row)

        csv_file.close()        

    except SystemExit:
        sys.exit(1)            
    except:
        import traceback
        exc_type, exc_value, exc_traceback = sys.exc_info()
        print '-'*60
        traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stdout)
        print '-'*60
        sys.exit(2)
