import base64
import hashlib
import hmac
import os
import requests
import selenium
import sys
from time import sleep
from urllib import quote
from selenium import webdriver

class SalesforceOAuth2(object):
    authorization_url = '/services/oauth2/authorize'
    token_url = '/services/oauth2/token'
    revoke_url = '/services/oauth2/revoke'

    def __init__(self, client_id, client_secret, redirect_uri, **kwargs):
        self.sandbox = kwargs.get('sandbox', False)

        if self.sandbox:
            self.auth_site = 'https://test.salesforce.com'
        else:
            self.auth_site = 'https://login.salesforce.com'

        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    def _request_token(self, data):
        import requests
        url = "{site}{token_url}".format(
            site=self.auth_site, token_url=self.token_url)
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        post_data = {'client_id': self.client_id,
                     'client_secret': self.client_secret}
        post_data.update(data)
        result = requests.post(url, data=post_data, headers=headers)
        return result, result.json()

    def authorize_url(self, **kwargs):
        from urllib import quote
        scope = kwargs.get('scope', quote('full'))
        fields = {
            'site': self.auth_site,
            'authorize_url': self.authorization_url,
            'clientid': self.client_id,
            'redirect_uri': quote(self.redirect_uri),
            'scope': scope
        }
        return "{site}{authorize_url}?response_type=code&client_id={clientid}&redirect_uri={redirect_uri}&scope={scope}".format(**fields)

    def get_token(self, code):
        from urllib import quote
        data = {
            'grant_type': 'authorization_code',
            'redirect_uri': self.redirect_uri,
            'code': code
        }
        response, response_json = self._request_token(data)
        if 'access_token' in response_json:
            self.access_token = response_json['access_token']
        if 'refresh_token' in response_json:
            self.refresh_token = response_json['refresh_token']
        return response_json

    def refresh_token(self, refresh_token):
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token
        }
        response, response_json = self._request_token(data)

        if 'access_token' in response_json:
            self.access_token = response_json['access_token']
        return response_json

    def generate_signature(self, id, issued_at):
        data = "{id}{issued}".format(id=id, issued=issued_at)
        digest = hmac.new(
            self.client_secret, data, digestmod=hashlib.sha256).digest()
        return base64.b64encode(digest).decode()

    def revoke_token(self, current_token):
        import requests
        from urllib import quote
        # Perform a GET request, because that's by far the easiest way
        url = "{site}{revoke_url}".format(
            site=self.auth_site, revoke_url=self.revoke_url)
        data = {
            'token': quote(current_token)
        }
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        return requests.post(url, data=data, headers=headers)

class PackageUpload(object):

    def __init__(self, instance_url, refresh_token, package, oauth_client_id, oauth_client_secret, oauth_callback_url, browser):
        self.instance_url = instance_url
        self.refresh_token = refresh_token
        self.package = package
        self.oauth_client_id = oauth_client_id
        self.oauth_client_secret = oauth_client_secret
        self.oauth_callback_url = oauth_callback_url
        self.browser = browser

    def build_package(self, build_name):
        """ Builds a managed package by calling SauceLabs via Selenium to click the Upload button """ 
        # Update Status
        print 'Starting browser'
        sys.stdout.flush()

        try:
            driver = self.get_selenium()
        except:
            print "Sleeping 5 more seconds to try again.  Last attempt to connect to Selenium failed"
            sleep(5)
            driver = self.get_selenium()

        driver.implicitly_wait(90) # seconds

        # Load the packages list page
        sleep(5) # Not sure why this sleep is necessary, but it seems to be
        driver.get('%s/0A2' % self.instance_url)

        # Update Status
        print 'Loaded package listing page'
        sys.stdout.flush()

        # Click the link to the package
        driver.find_element_by_xpath("//th[contains(@class,'dataCell')]/a[text()='%s']" % self.package).click()

        # Update Status
        print 'Loaded package page'
        sys.stdout.flush()

        # Click the Upload button to open the upload form
        driver.find_element_by_xpath("//input[@class='btn' and @value='Upload']").click()

        # Update Status
        print 'Loaded Upload form'
        sys.stdout.flush()

        # Populate and submit the upload form to create a beta managed package
        name_input = driver.find_element_by_id('ExportPackagePage:UploadPackageForm:PackageDetailsPageBlock:PackageDetailsBlockSection:VersionInfoSectionItem:VersionText')
        name_input.clear()
        name_input.send_keys(build_name)
        driver.find_element_by_id('ExportPackagePage:UploadPackageForm:PackageDetailsPageBlock:PackageDetailsPageBlockButtons:bottom:upload').click()

        # Update Status
        print 'Upload Submitted'
        sys.stdout.flush()

        # Monitor the package upload progress
        retry_count = 0
        last_status = None
        while True:
            try:
                status_message = driver.find_element_by_css_selector('.messageText').text
            except selenium.common.exceptions.StaleElementReferenceException:
                # These come up, possibly if you catch the page in the middle of updating the text via javascript
                sleep(1)
                continue
            except selenium.common.exceptions.NoSuchElementException:
                # These come up, possibly if you catch the page in the middle of updating the text via javascript
                if retry_count > 15:
                    print ".messageText not found after 15 retries"
                    break
                sleep(1)
                retry_count += 1
                continue

            retry_count = 0

            if status_message.startswith('Upload Complete'):
                # Update Status
                print status_message
                sys.stdout.flush()
    
                # Get the version number and install url
                version = driver.find_element_by_xpath("//th[text()='Version Number']/following-sibling::td/span").text
                install_url = driver.find_element_by_xpath("//a[contains(@name, ':pkgInstallUrl')]").get_attribute('href')
            
                self.version = version
                self.install_url = install_url
    
                break

            if status_message.startswith('Upload Failed'):
                print status_message
                sys.stdout.flush()
                break 

            # Update Status
            if status_message != last_status:
                print status_message
                sys.stdout.flush()
            last_status = status_message

            sleep(1)

        driver.quit()    


    def refresh(self):
        sf = SalesforceOAuth2(self.oauth_client_id, self.oauth_client_secret, self.oauth_callback_url)
        refresh_response = sf.refresh_token(self.refresh_token)
        if refresh_response.get('access_token', None):
            self.access_token = refresh_response['access_token']

    def get_selenium(self):
        # Always refresh the token to ensure a long enough session to build the package
        self.refresh()
        start_url = '%s/secur/frontdoor.jsp?sid=%s' % (self.instance_url, self.access_token)

        driver = getattr(webdriver, self.browser)()
        #driver = webdriver.Firefox()
        driver.get(start_url)
        return driver

def package_upload():
    oauth_client_id = os.environ.get('OAUTH_CLIENT_ID')
    oauth_client_secret = os.environ.get('OAUTH_CLIENT_SECRET')
    oauth_callback_url = os.environ.get('OAUTH_CALLBACK_URL')
    instance_url = os.environ.get('INSTANCE_URL')
    refresh_token = os.environ.get('REFRESH_TOKEN')
    package = os.environ.get('PACKAGE')
    build_name = os.environ.get('BUILD_NAME')
    build_commit = os.environ.get('BUILD_COMMIT')
    build_workspace = os.environ.get('BUILD_WORKSPACE')
    browser = os.environ.get('SELENIUM_BROWSER', 'Firefox')
    
    uploader = PackageUpload(instance_url, refresh_token, package, oauth_client_id, oauth_client_secret, oauth_callback_url, browser)
    uploader.build_package(build_name)
    
    print 'Build Complete'
    print '-------------------'
    print 'Version: %s' % uploader.version
    print 'Install URL: %s' % uploader.install_url
    print 'Writing package.properties file'
    sys.stdout.flush()
    f = open('%s/package.properties' % build_workspace, 'w')
    f.write('PACKAGE_VERSION=%s\n' % uploader.version)
    f.write('INSTALL_URL=%s\n' % uploader.install_url)
    f.write('BUILD_COMMIT=%s\n' % build_commit)
    f.close()

if __name__ == '__main__':
    try:
        package_upload()
    except:
        import traceback
        exc_type, exc_value, exc_traceback = sys.exc_info()
        print '-'*60
        traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stdout)
        print '-'*60
        sys.exit(1)

