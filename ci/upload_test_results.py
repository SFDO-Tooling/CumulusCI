import json
import os
import sys
import requests

def upload_test_results():
    APEXTESTSDB_BASE_URL=os.environ.get('APEXTESTSDB_BASE_URL')
    APEXTESTSDB_USER_ID=os.environ.get('APEXTESTSDB_USER_ID')
    APEXTESTSDB_TOKEN=os.environ.get('APEXTESTSDB_TOKEN')

    PACKAGE=os.environ.get('PACKAGE')
    REPOSITORY_URL=os.environ.get('REPOSITORY_URL')
    BRANCH_NAME=os.environ.get('BRANCH_NAME')
    COMMIT_SHA=os.environ.get('COMMIT_SHA')
    EXECUTION_NAME=os.environ.get('EXECUTION_NAME')
    EXECUTION_URL=os.environ.get('EXECUTION_URL')
    RESULTS_FILE_URL=os.environ.get('RESULTS_FILE_URL')
    ENVIRONMENT_NAME=os.environ.get('ENVIRONMENT_NAME')

    payload = {
        'package': PACKAGE,
        'repository_url': REPOSITORY_URL,
        'branch_name': BRANCH_NAME,
        'commit_sha': COMMIT_SHA,
        'execution_name': EXECUTION_NAME,
        'execution_url': EXECUTION_URL,
        'environment_name': ENVIRONMENT_NAME,
        'user': APEXTESTSDB_USER_ID,
        'token': APEXTESTSDB_TOKEN,
        'results_file_url': RESULTS_FILE_URL,
    }

    response = requests.post(APEXTESTSDB_BASE_URL + '/upload_test_result', data=payload)
    try:
        data = json.loads(response.content)
    except ValueError:
        print response.content

    return '%s/executions/%s' % (APEXTESTSDB_BASE_URL, data['execution_id'])

if __name__ == '__main__':
    try:
        execution_detail_url = upload_test_results()
        print execution_detail_url
    except:
        import traceback
        exc_type, exc_value, exc_traceback = sys.exc_info()
        print '-'*60
        traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stdout)
        print '-'*60
        sys.exit(1)
