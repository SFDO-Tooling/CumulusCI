import os
import re
import sys
from time import sleep
import datetime
import calendar
import collections
import json
from simple_salesforce import Salesforce

def log_time_delta(start, end):
    """ Returns microsecond difference between two debug log timestamps
        in the format HH:MM:SS.micro
    """
    dummy_date = datetime.date(2001,1,1)
    dummy_date_next = datetime.date(2001,1,2)
    
    # Split out the parts of the start and end string
    start_parts = re.split(':|\.', start)
    start_parts = [int(part) for part in start_parts]
    start_parts[3] = start_parts[3] * 1000
    t_start = datetime.time(*start_parts)

    end_parts = re.split(':|\.', end)
    end_parts = [int(part) for part in end_parts]
    end_parts[3] = end_parts[3] * 1000
    t_end = datetime.time(*end_parts)

    # Combine with dummy date to do date math
    d_start = datetime.datetime.combine(dummy_date, t_start)
    
    # If end was on the next day, attach to next dummy day
    if start_parts[0] > end_parts[0]:
        d_end = datetime.datetime.combine(dummy_date_next, t_end)
    else:
        d_end = datetime.datetime.combine(dummy_date, t_end)

    delta = d_end - d_start

    return delta.total_seconds()

def parse_log(class_name, log):
    methods = {}
    for method, stats in parse_log_by_method(class_name, log):
        methods[method] = stats
    return methods
    
def parse_log_by_method(class_name, log):
    stats = {}
    in_limits = False
    unit = None
    method = None
    for line in log:
        # Strip newline character
        line = line.strip()

        if line.find('|CODE_UNIT_STARTED|[EXTERNAL]|01p') != -1:
            # Parse the method name
            unit = line.split('|')[-1]
            if not unit.startswith(class_name + '.'):
                # Skip child code units (i.e. triggers, Global Scheduler, etc)
                continue
            method = unit.split('.')[-1]
            start_timestamp = line.split(' ')[0]
            continue

        # NOTE: If we are in a child code unit of the test method, this section
        # will currently set the limits for the child.  However, they will later
        # be overwritten by the test method's limits when they are parsed.  Since
        # nothing is yielded until the end of the test method's code limit, this
        # should be safe for now but should be refactored soon.
        if line.find('|LIMIT_USAGE_FOR_NS|(default)|') != -1:
            # Parse the start of the limits section
            in_limits = True
            continue

        if in_limits and line.find(':') == -1:
            # Parse the end of the limits section
            in_limits = False
            continue

        if in_limits:
            # Parse the limit name, used, and allowed values
            limit, value = line.split(': ')
            used, allowed = value.split(' out of ')
            stats[limit] = {
                'used': used,
                'allowed': allowed,
            }
            continue

        if line.find('|CODE_UNIT_FINISHED|%s.%s' % (class_name, method)) != -1:
            end_timestamp = line.split(' ')[0]
            stats['duration'] = log_time_delta(start_timestamp, end_timestamp)

            # Yield the stats for the method
            yield method, stats
            stats = {}
            in_limits = False
        
        # If debug log size limit was reached, fail gracefully
        if line.find('* MAXIMUM DEBUG LOG SIZE REACHED *') != -1:
            break
        

def run_tests():
    username = os.environ.get('SF_USERNAME')
    password = os.environ.get('SF_PASSWORD')
    serverurl = os.environ.get('SF_SERVERURL')
    test_name_match = os.environ.get('APEX_TEST_NAME_MATCH', '%_TEST')
    test_name_exclude = os.environ.get('APEX_TEST_NAME_EXCLUDE', '')
    namespace = os.environ.get('NAMESPACE', None)
    poll_interval = int(os.environ.get('POLL_INTERVAL', 10))
    debug = os.environ.get('DEBUG_TESTS',False) == 'true'
    debug_logdir = os.environ.get('DEBUG_LOGDIR')
    json_output = os.environ.get('TEST_JSON_OUTPUT', None)
    
    if namespace:
        namespace = "'%s'" % namespace
    else:
        namespace = 'null'
    
    sandbox = False
    if serverurl.find('test.salesforce.com') != -1:
        sandbox = True
    
    sf = Salesforce(username=username, password=password, security_token='', sandbox=sandbox, version='32.0')
    
    # Change base_url to use the tooling api
    sf.base_url = sf.base_url + 'tooling/'
    
    # Split test_name_match by commas to allow multiple class name matching options
    where_name = []
    for pattern in test_name_match.split(','):
        if pattern:
            where_name.append("Name LIKE '%s'" % pattern)

    # Add any excludes to the where clause
    where_exclude = []
    for pattern in test_name_exclude.split(','):
        if pattern:
            where_exclude.append("(NOT Name LIKE '%s')" % pattern)
   
    # Get all test classes for namespace
    query = "SELECT Id, Name FROM ApexClass WHERE NamespacePrefix = %s" % namespace
    if where_name:
        query += " AND (%s)" % ' OR '.join(where_name)
    if where_exclude:
        query += " AND %s" % ' AND '.join(where_exclude)

    print "Running Query: %s" % query
    sys.stdout.flush()

    res = sf.query_all(query)

    print "Found %s classes" % res['totalSize']
    sys.stdout.flush()

    if not res['totalSize']:
        return {'Pass': 0, 'Fail': 0, 'CompileFail': 0, 'Skip': 0}
    
    classes_by_id = {}
    classes_by_name = {}
    traces_by_class_id = {}
    results_by_class_name = {}
    classes_by_log_id = {}
    logs_by_class_id = {}
    
    for cls in res['records']:
        classes_by_id[cls['Id']] = cls['Name']
        classes_by_name[cls['Name']] = cls['Id']
        results_by_class_name[cls['Name']] = {}

    # If debug is turned on, setup debug traces for all test classes
    if debug:
        # Set up a simple-salesforce sobject for TraceFlag using the tooling api
        TraceFlag = sf.TraceFlag
        TraceFlag.base_url = (u'https://{instance}/services/data/v{sf_version}/tooling/sobjects/{object_name}/'
                     .format(instance=sf.sf_instance,
                             object_name='TraceFlag',
                             sf_version=sf.sf_version))

        # First, delete any old trace flags still lying around
        tf_res = sf.query('Select Id from TraceFlag')
        if tf_res['totalSize']:
            for tf in tf_res['records']:
                TraceFlag.delete(tf['Id'])
    
        expiration = datetime.datetime.now() + datetime.timedelta(1)
        for class_id in classes_by_id.keys():
            res = TraceFlag.create({
                'ApexCode': 'Error',
                'ApexProfiling': 'Debug',
                'Callout': 'Error',
                'Database': 'Error',
                'ExpirationDate': expiration.isoformat(),
                #'ScopeId': class_id,
                'System': 'Error',
                'TracedEntityId': class_id,
                'Validation': 'Error',
                'Visualforce': 'Error',
                'Workflow': 'Error',
            })
            traces_by_class_id[class_id] = res['id']
    
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
    res = sf.query_all("SELECT StackTrace,Message, ApexLogId, AsyncApexJobId,MethodName, Outcome, ApexClassId, TestTimestamp FROM ApexTestResult WHERE AsyncApexJobId = '%s'" % job_id)
    
    counts = {
        'Pass': 0,
        'Fail': 0,
        'CompileFail': 0,
        'Skip': 0,
    }
    for result in res['records']:
        class_name = classes_by_id[result['ApexClassId']]
        results_by_class_name[class_name][result['MethodName']] = result
        counts[result['Outcome']] += 1
        if debug and result['ApexLogId']:
            classes_by_log_id[result['ApexLogId']] = result['ApexClassId']
    
    # Fetch debug logs if debug is enabled
    if debug:
        log_ids = "('%s')" % "','".join([str(id) for id in classes_by_log_id.keys()])
        res = sf.query_all("SELECT Id, Application, DurationMilliseconds, Location, LogLength, LogUserId, Operation, Request, StartTime, Status from ApexLog where Id in %s" % log_ids)
        for log in res['records']:
            class_id = classes_by_log_id[log['Id']]
            class_name = classes_by_id[class_id]
            logs_by_class_id[class_id] = log
            # Fetch the debug log file
            body_url = '%ssobjects/ApexLog/%s/Body' % (sf.base_url, log['Id'])
            resp = sf.request.get(body_url, headers=sf.headers)
            log_file = class_name + '.log'
            if debug_logdir:
                log_file = debug_logdir + os.sep + log_file
            f = open(log_file, 'w')
            f.write(resp.content)
            f.close()

            # Parse stats from the log file
            f = open(log_file, 'r')
            method_stats = parse_log(class_name, f)
            
            # Add method stats to results_by_class_name
            for method, stats in method_stats.items():
                results_by_class_name[class_name][method]['stats'] = stats

        # Delete the trace flags
        for trace_id in traces_by_class_id.values():
            TraceFlag.delete(trace_id)

    # Build an OrderedDict of results
    test_results = []

    class_names = results_by_class_name.keys()
    class_names.sort()
    for class_name in class_names:
        class_id = classes_by_name[class_name]
        duration = None
        if debug and class_id in logs_by_class_id:
            duration = int(logs_by_class_id[class_id]['DurationMilliseconds']) * .001
            print 'Class: %s (%ss)' % (class_name, duration)
        else:
            print 'Class: %s' % class_name
        sys.stdout.flush()

        method_names = results_by_class_name[class_name].keys()
        method_names.sort()
        for method_name in method_names:
            result = results_by_class_name[class_name][method_name]

            test_results.append({
                'ClassName': class_name,
                'Method': result['MethodName'],
                'Message': result['Message'],
                'Outcome': result['Outcome'],
                'StackTrace': result['StackTrace'],
                'Stats': result.get('stats', None),
                'TestTimestamp': result.get('TestTimestamp', None),
            })
    
            # Output result for method
            print '   %(Outcome)s: %(MethodName)s' % result

            if debug:
                print '     DEBUG LOG INFO:'
                stats = result.get('stats',None)
                if not stats:
                    print '       No stats found, likely because of debug log size limit'
                else:
                    stat_keys = stats.keys()
                    stat_keys.sort()
                    for stat in stat_keys:
                        try:
                            value = stats[stat]
                            output = '       %s / %s' % (value['used'], value['allowed'])
                            print output.ljust(26) + stat
                        except:
                            output = '       %s' % stats[stat]
                            print output.ljust(26) + stat
    
            # Print message and stack trace if failed
            if result['Outcome'] in ['Fail','CompileFail']:
                print '   Message: %(Message)s' % result
                print '   StackTrace: %(StackTrace)s' % result
            sys.stdout.flush()
    
    print '-------------------------------------------------------------------------------'
    print 'Passed: %(Pass)s  Fail: %(Fail)s  Compile Fail: %(CompileFail)s  Skipped: %(Skip)s' % counts
    print '-------------------------------------------------------------------------------'
    sys.stdout.flush()

    if json_output:
        f = open(json_output, 'w')
        f.write(json.dumps(test_results))
        f.close()

    return counts

if __name__ == '__main__':
    try:
        counts = run_tests()
        # Exit with status 1 if test failures occurred
        if counts['Fail'] or counts['CompileFail'] or counts['Skip']:
            sys.exit(1)
    except SystemExit:
        sys.exit(1)            
    except:
        import traceback
        exc_type, exc_value, exc_traceback = sys.exc_info()
        print '-'*60
        traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stdout)
        print '-'*60
        sys.exit(1)
