import os
import sys
from time import sleep
from simple_salesforce import Salesforce

def run_tests():
    username = os.environ.get('SF_USERNAME')
    password = os.environ.get('SF_PASSWORD')
    serverurl = os.environ.get('SF_SERVERURL')
    test_name_match = os.environ.get('APEX_TEST_NAME_MATCH', '%_TEST')
    namespace = os.environ.get('NAMESPACE', None)
    poll_interval = int(os.environ.get('POLL_INTERVAL', 10))
    
    if namespace:
        namespace = "'%s'" % namespace
    else:
        namespace = 'null'
    
    sandbox = False
    if serverurl.find('test.salesforce.com') != -1:
        sandbox = True
    
    sf = Salesforce(username=username, password=password, security_token='', sandbox=sandbox)
    
    # Change base_url to use the tooling api
    sf.base_url = sf.base_url + 'tooling/'
    
    # Get all test classes for namespace
    print "Querying ApexClasses with NamespacePrefix = %s and Name like '%s'" % (namespace, test_name_match)
    sys.stdout.flush()
    res = sf.query_all("SELECT Id, Name FROM ApexClass WHERE NamespacePrefix = %s and Name LIKE '%s'" % (namespace, test_name_match))
    print "Found %s classes" % res['totalSize']
    sys.stdout.flush()

    if not res['totalSize']:
        return {'Pass': 0, 'Failed': 0, 'CompileFail': 0, 'Skip': 0}
    
    classes_by_id = {}
    results_by_class_name = {}
    
    for cls in res['records']:
        classes_by_id[cls['Id']] = cls['Name']
        results_by_class_name[cls['Name']] = {}
    
    # Run all the tests
    print "Queuing tests for execution..."
    sys.stdout.flush()
    job_id = sf.restful('runTestsAsynchronous', params={'classids': ','.join(classes_by_id.keys())})
    
    # Loop waiting for the tests to complete
    while True:
        res = sf.query_all("SELECT Id, Status, ApexClassId FROM ApexTestQueueItem WHERE ParentJobId = '%s'" % job_id)
        counts = {
            'Queued': 0,
            'Processing': 0,
            'Aborted': 0,
            'Completed': 0,
            'Failed': 0,
            'Preparing': 0,
            'Holding': 0,
        }
        for item in res['records']:
            counts[item['Status']] += 1
    
        # If all tests have run, break from the loop
        if not counts['Queued'] and not counts['Processing']:
            print ''
            print '-------------------------------------------------------------------------------'
            print 'Test Results'
            print '-------------------------------------------------------------------------------'
            sys.stdout.flush()
            break
        
        print 'Completed: %(Completed)s  Processing: %(Processing)s  Queued: %(Queued)s' % counts
        sys.stdout.flush()
        sleep(poll_interval)
    
    # Get the test results by method
    res = sf.query_all("SELECT StackTrace,Message, AsyncApexJobId,MethodName, Outcome, ApexClassId FROM ApexTestResult WHERE AsyncApexJobId = '%s'" % job_id)
    
    counts = {
        'Pass': 0,
        'Failed': 0,
        'CompileFail': 0,
        'Skip': 0,
    }
    for result in res['records']:
        class_name = classes_by_id[result['ApexClassId']]
        results_by_class_name[class_name][result['MethodName']] = result
        counts[result['Outcome']] += 1
    
    class_names = results_by_class_name.keys()
    class_names.sort()
    for class_name in class_names:
        print 'Class: %s' % class_name
        sys.stdout.flush()
        method_names = results_by_class_name[class_name].keys()
        method_names.sort()
        for method_name in method_names:
            result = results_by_class_name[class_name][method_name]
    
            # Output result for method
            print '   %(Outcome)s: %(MethodName)s' % result
    
            # Print message and stack trace if failed
            if result['Outcome'] in ['Failed','CompileFail']:
                print '   Message: %(Message)s' % result
                print '   StackTrace: %(StackTrace)s' % result
            sys.stdout.flush()
    
    print '-------------------------------------------------------------------------------'
    print 'Passed: %(Pass)s  Failed: %(Failed)s  Compile Fail: %(CompileFail)s  Skipped: %(Skip)s' % counts
    print '-------------------------------------------------------------------------------'
    sys.stdout.flush()

    return counts

if __name__ == '__main__':
    try:
        counts = run_tests()
        # Exit with status 1 if test failures occurred
        if counts['Failed'] or counts['CompileFail'] or counts['Skip']:
            sys.exit(1)
            
    except:
        import traceback
        exc_type, exc_value, exc_traceback = sys.exc_info()
        print '-'*60
        traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stdout)
        print '-'*60
        sys.exit(1)
