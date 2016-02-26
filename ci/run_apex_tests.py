import os
import re
import sys
import cgi
import codecs
from time import sleep
import datetime
import calendar
import collections
import json
from simple_salesforce import Salesforce

# Force UTF8 output
reload(sys)
sys.setdefaultencoding('UTF8')

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

def decode_to_unicode(content):
    if content:
        try:
            # Try to decode ISO-8859-1 to unicode
            return content.decode('ISO-8859-1')
        except UnicodeEncodeError:
            # If decoding ISO-8859 failed, assume content is unicode already
            return content

def parse_log(class_name, log):
    class_name = decode_to_unicode(class_name)
    methods = {}
    for method, stats, children in parse_log_by_method(class_name, log):
        methods[method] = {
            'stats': stats,
            'children': children,
        }
    return methods

def parse_unit_started(class_name, line):
    unit = line.split('|')[-1]

    unit_type = 'other'
    unit_info = {}

    # test_method
    if unit.startswith(class_name + '.'):
        unit_type = 'test_method'
        unit = unit.split('.')[-1]

    # trigger
    elif unit.find('trigger event') != -1:
        unit_type = 'trigger'
        unit, obj, event = re.match(r'(.*) on (.*) trigger event (.*) for.*', unit).groups()
        unit_info = {
            'event': event,
            'object': obj,
        }

    # Add the start timestamp to unit_info
    unit_info['start_timestamp'] = line.split(' ')[0]

    return unit, unit_type, unit_info

def parse_log_by_method(class_name, log):
    stats = {}
    last_stats = {}
    in_limits = False
    in_cumulative_limits = False
    in_testing_limits = False
    unit = None
    method = None
    children = {}
    parent = None

    for line in log:
        # Strip newline character
        line = decode_to_unicode(line).strip()

        if line.find('|CODE_UNIT_STARTED|[EXTERNAL]|') != -1:
            unit, unit_type, unit_info = parse_unit_started(class_name, line)
            
            if unit_type == 'test_method':
                method = decode_to_unicode(unit)
                method_unit_info = unit_info
                #children = {}
                children = []
                stack = []
            else:
                #if unit_type not in children:
                #    children[unit_type] = {}
                #if unit not in children[unit_type]:
                #    children[unit_type][unit] = []
                #children[unit_type][unit].append({
                #    'stats': {},
                #    'unit_info': unit_info,
                #})
                stack.append({
                    'unit': unit,
                    'unit_type': unit_type,
                    'unit_info': unit_info,
                    'stats': {},
                    'children': [],
                })

            continue

        if line.find('|CUMULATIVE_LIMIT_USAGE') != -1 and line.find('USAGE_END') == -1:
            in_cumulative_limits = True
            in_testing_limits = False
            continue

        if line.find('|TESTING_LIMITS') != -1:
            in_testing_limits = True
            in_cumulative_limits = False
            continue

        if line.find('|LIMIT_USAGE_FOR_NS|(default)|') != -1:
            # Parse the start of the limits section
            in_limits = True
            continue

        if in_limits and line.find(':') == -1:
            # Parse the end of the limits section
            in_limits = False
            in_cumulative_limits = False
            in_testing_limits = False
            continue

        if in_limits:
            # Parse the limit name, used, and allowed values
            limit, value = line.split(': ')
            if in_testing_limits:
                limit = 'TESTING_LIMITS: {0}'.format(limit,)
            used, allowed = value.split(' out of ')
            stats[limit] = {
                'used': used,
                'allowed': allowed,
            }
            continue

        # Handle the finish of test methods
        if line.find(u'|CODE_UNIT_FINISHED|{0}.{1}'.format(class_name, method)) != -1:
            end_timestamp = line.split(' ')[0]
            stats['duration'] = log_time_delta(method_unit_info['start_timestamp'], end_timestamp)
    
            # Yield the stats for the method
            yield method, stats, children
            last_stats = stats.copy()
            stats = {}
            in_cumulative_limits = False
            in_limits = False
        # Handle all other code units finishing
        elif line.find('|CODE_UNIT_FINISHED|') != -1:
            end_timestamp = line.split(' ')[0]
            stats['duration'] = log_time_delta(method_unit_info['start_timestamp'], end_timestamp)
 
            try: 
                child = stack.pop()
            except:
                # Skip if there was no stack.  This seems to have have started in Spring 16
                # where the debug log will contain CODE_UNIT_FINISHED lines which have no matching
                # CODE_UNIT_STARTED from earlier in the file
                continue
            child['stats'] = stats
  
            # If the stack is now empty, add the child to the main children list
            if not stack:
                children.append(child)
            # If the stack is not empty, add this child to its parent
            else:
                stack[-1]['children'].append(child)
                
            # Add the stats to the children dict
            #children[unit_type][unit][-1]['stats'] = stats
 
            stats = {}
            in_cumulative_limits = False
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
    debug = os.environ.get('DEBUG_TESTS',False) in ['true','True']
    debug_logdir = os.environ.get('DEBUG_LOGDIR')
    json_output = os.environ.get('TEST_JSON_OUTPUT', None)
    junit_output = os.environ.get('TEST_JUNIT_OUTPUT', None)
    
    if namespace:
        namespace = "'{0}'".format(namespace,)
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
            where_name.append("Name LIKE '{0}'".format(pattern))

    # Add any excludes to the where clause
    where_exclude = []
    for pattern in test_name_exclude.split(','):
        if pattern:
            where_exclude.append("(NOT Name LIKE '{0}')".format(pattern,))
   
    # Get all test classes for namespace
    query = "SELECT Id, Name FROM ApexClass WHERE NamespacePrefix = {0}".format(namespace,)
    if where_name:
        query += " AND ({0})".format(' OR '.join(where_name),)
    if where_exclude:
        query += " AND {0}".format(' AND '.join(where_exclude),)

    print "Running Query: {0}".format(query,)
    sys.stdout.flush()

    res = sf.query_all(query)

    print "Found {0} classes".format(res['totalSize'],)
    sys.stdout.flush()

    if not res['totalSize']:
        return {'Pass': 0, 'Fail': 0, 'CompileFail': 0, 'Skip': 0}
    
    classes_by_id = {}
    classes_by_name = {}
    trace_id = None
    results_by_class_name = {}
    classes_by_log_id = {}
    logs_by_class_id = {}
    
    for cls in res['records']:
        classes_by_id[cls['Id']] = cls['Name']
        classes_by_name[cls['Name']] = cls['Id']
        results_by_class_name[cls['Name']] = {}

    # If debug is turned on, setup debug traces for all test classes
    if debug:
        print 'Setting up trace flag to capture debug logs'

        # Get the User's id to set a TraceFlag
        res_user = sf.query("Select Id from User where Username = '{0}'".format(username,))
        user_id = res_user['records'][0]['Id']
        
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
    
        expiration = datetime.datetime.now() + datetime.timedelta(seconds=60*60*12)
        res = TraceFlag.create({
            'ApexCode': 'Info',
            'ApexProfiling': 'Debug',
            'Callout': 'Info',
            'Database': 'Info',
            'ExpirationDate': expiration.isoformat(),
            #'ScopeId': user_id,
            'System': 'Info',
            'TracedEntityId': user_id,
            'Validation': 'Info',
            'Visualforce': 'Info',
            'Workflow': 'Info',
        })
        trace_id = res['id']

        print 'Created TraceFlag for user'
    
    # Run all the tests
    print "Queuing tests for execution..."
    sys.stdout.flush()
    job_id = sf.restful('runTestsAsynchronous', params={'classids': ','.join(classes_by_id.keys())})
    
    # Loop waiting for the tests to complete
    while True:
        res = sf.query_all("SELECT Id, Status, ApexClassId FROM ApexTestQueueItem WHERE ParentJobId = '{0}'".format(job_id,))
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
    res = sf.query_all("SELECT StackTrace,Message, ApexLogId, AsyncApexJobId,MethodName, Outcome, ApexClassId, TestTimestamp FROM ApexTestResult WHERE AsyncApexJobId = '{0}'".format(job_id,))
    
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
        log_ids = "('{0}')".format("','".join([str(id) for id in classes_by_log_id.keys()]),)
        res = sf.query_all("SELECT Id, Application, DurationMilliseconds, Location, LogLength, LogUserId, Operation, Request, StartTime, Status from ApexLog where Id in {0}".format(log_ids,))
        for log in res['records']:
            class_id = classes_by_log_id[log['Id']]
            class_name = classes_by_id[class_id]
            logs_by_class_id[class_id] = log
            # Fetch the debug log file
            body_url = '{0}sobjects/ApexLog/{1}/Body'.format(sf.base_url, log['Id'])
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
            for method, info in method_stats.items():
                results_by_class_name[class_name][method].update(info)

        # Delete the trace flag
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
            print 'Class: {0} ({1}s)'.format(class_name, duration)
        else:
            print 'Class: {0}'.format(class_name,)
        sys.stdout.flush()

        method_names = results_by_class_name[class_name].keys()
        method_names.sort()
        for method_name in method_names:
            result = results_by_class_name[class_name][method_name]

            test_results.append({
                'Children': result.get('children', None),
                'ClassName': decode_to_unicode(class_name),
                'Method': decode_to_unicode(result['MethodName']),
                'Message': decode_to_unicode(result['Message']),
                'Outcome': decode_to_unicode(result['Outcome']),
                'StackTrace': decode_to_unicode(result['StackTrace']),
                'Stats': result.get('stats', None),
                'TestTimestamp': result.get('TestTimestamp', None),
            })
            
            # Output result for method
            if debug and json_output and result.get('stats') and 'duration' in result['stats']:
                # If debug is enabled and we're generating the json output, include duration with the test
                print u'   {0}: {1} ({2}s)'.format(
                    result['Outcome'], 
                    result['MethodName'], 
                    result['stats']['duration']
                )
            else:
                print u'   {Outcome}: {MethodName}'.format(**result)

            if debug and not json_output:
                print u'     DEBUG LOG INFO:'
                stats = result.get('stats',None)
                if not stats:
                    print u'       No stats found, likely because of debug log size limit'
                else:
                    stat_keys = stats.keys()
                    stat_keys.sort()
                    for stat in stat_keys:
                        try:
                            value = stats[stat]
                            output = u'       {0} / {1}'.format(value['used'], value['allowed'])
                            print output.ljust(26) + stat
                        except:
                            output = u'       {0}'.format(stats[stat],)
                            print output.ljust(26) + stat
    
            # Print message and stack trace if failed
            if result['Outcome'] in ['Fail','CompileFail']:
                print u'   Message: {Message}'.format(**result)
                print u'   StackTrace: {StackTrace}'.format(**result)
            sys.stdout.flush()
    
    print u'-------------------------------------------------------------------------------'
    print u'Passed: %(Pass)s  Fail: %(Fail)s  Compile Fail: %(CompileFail)s  Skipped: %(Skip)s' % counts
    print u'-------------------------------------------------------------------------------'
    sys.stdout.flush()
    
    if counts['Fail'] or counts['CompileFail']:
        print u''
        print u'Failing Tests'
        print u'-------------'
        print u''
        sys.stdout.flush()

        counter = 0
        for result in test_results:
            if result['Outcome'] not in ['Fail','CompileFail']:
                continue
            counter += 1
            print u'{0}: {1}.{2} - {3}'.format(counter, result['ClassName'], result['Method'], result['Outcome'])
            print u'  Message: {0}'.format(result['Message'],)
            print u'  StackTrace: {0}'.format(result['StackTrace'],)
            sys.stdout.flush()

    if json_output:
        f = codecs.open(json_output, encoding='utf-8', mode='w')
        f.write(json.dumps(test_results))
        f.close()

    if junit_output:
        f = codecs.open(junit_output, encoding='utf-8', mode='w')
        f.write('<testsuite tests="{0}">\n'.format(len(test_results)),)
        for result in test_results:
            testcase = '  <testcase classname="{0}" name="{1}"'.format(result['ClassName'], result['Method'])
            if 'Stats' in result and result['Stats'] and 'duration' in result['Stats']:
                testcase = '{0} time="{1}"'.format(testcase, result['Stats']['duration'])
            if result['Outcome'] in ['Fail','CompileFail']:
                testcase = '{0}>\n'.format(testcase,)
                testcase = '{0}    <failure type="{1}">{2}</failure>\n'.format(
                    testcase, 
                    cgi.escape(result['StackTrace']), 
                    cgi.escape(result['Message']),
                )
                testcase = '{0}  </testcase>\n'.format(testcase,)
            else:
                testcase = '{0} />\n'.format(testcase,)
            f.write(testcase)

        f.write('</testsuite>')
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
        sys.exit(2)
