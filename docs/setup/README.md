# CumulusCI - Installation and Setup

This document details the process of setting up the infrastructure to support the Continuous Integration process for the Cumulus project.  The scripts and instructions should be reusable in other projects with minimal adjustments.  The process integrates Force.com Developer Edition or Partner Developer Edition orgs with a Force.com project repository hosted on Github including support for private Github repositories.

This document covers:

* Installing Jenkins on the Server
* Configuring Jenkins
    * Installing Plugins
    * Configuring Github authentication
    * Installing custom scripts from this repostory

For an overview of the process, see the [Cumulus Continuous Integration Process documentation](https://github.com/SalesforceFoundation/CumulusCI).

# Prerequisites

## Github Repository

For this process to work against a Force.com project housed on Github, the following criteria must be met:

1. The repository must have a build.xml file in the repository root which contains the following targets:

	* **deploy** - Standard Ant Migration Tool deployment of the package running all tests
	* **deployWithoutTest** - Standard Ant Migration Tool deployment of the package without tests
	* **upgradeDependentPackages** - Ant target which upgrades any dependent managed packages to the correct version.  If your package does not depend on other managed packages, you can skip this target and adjust the job configuration accordingly.
	* **deployCI** - Ant target which can successfully deploy the code to a new, untouched DE org.
2. The deployCI target must also run multiple times against the same org to cleanly deploy different branches of the code.  This means the deployCI target is also responsible for ensuring no stale metadata exists in the org from a previous build and that any dependent managed packages.
3. The main branch of the repository is named **dev**.  This is done to prevent ambiguity in calling the main branch master as some people use master to mean the latest development branch while others use it to signify the production branch.


## Server
The load on the build server is fairly light since most of the build and test execution is happening via calls to the Force.com Metadata API.

Our server runs Ubuntu 13.04 (Raring Ringtail) (PVHVM beta) but the instructions in this document would likely work for any Ubuntu release.  They could also be used for other Linux distributions if you adjust the apt-get commands to the appropriate packaging framework.

The original Jenkins server was setup on an AWS micro instance which was then upgraded to the mini instance.  We experienced a number of performance issues with builds including the web frontend of Jenkins failing to respond causing a 503 from nginx.  After switching to a 2GB Rackspace Cloud Server, we have experienced no performance issues.  This is not to say running the build server on AWS is not possible, but it seems to require some investment in tuning the instance correctly which was easily avoided with the Rackspace Cloud Server.

# Server Configuration

## Installing Jenkins

Assuming a brand new Ubuntu 13.04 server, the following commands should be sufficient to install Jenkins:

	wget -q -O - http://pkg.jenkins-ci.org/debian/jenkins-ci.org.key | sudo apt-key add -
	sudo sh -c 'echo deb http://pkg.jenkins-ci.org/debian binary/ > /etc/apt/sources.list.d/jenkins.list'
	sudo apt-get update
	sudo apt-get install jenkins
	
## Installing and Configuring Nginx
By default, Jenkins listens on port 8080.  To host on port 80, we use nginx in front of Jenkins:

	sudo aptitude -y install nginx
	cd /etc/nginx/sites-available
	sudo rm default ../sites-enabled/default
	sudo vi jenkins
	
The contents of the jenkins file should be similar to the following, adjusted for hostname:

	upstream app_server {
	    server 127.0.0.1:8080 fail_timeout=0;
	}

	server {
	    listen 80;
	    listen [::]:80 default ipv6only=on;
	    server_name ci.yourdomain.org;

	    location / {
	        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
	        proxy_set_header Host $http_host;
	        proxy_redirect off;
	
	        if (!-f $request_filename) {
	            proxy_pass http://app_server;
	            break;
	        }
	    }
	}
	
Once your edits are complete, link the jenkins file into sites-enabled and restart nginx:

	sudo ln -s /etc/nginx/sites-available/jenkins /etc/nginx/sites-enabled/
	sudo service nginx restart
	
You should now be able to hit your Jenkins instance proxied through nginx at http://ci.yourdomain.org

## Configuring Postfix
For Jenkins to send emails on build failure, smtp on localhost needs to work.  We use a gmail account to send the emails.  The following commands will setup postfix to send email through a Gmail account (taken from [this article by Rahul Bansal](https://rtcamp.com/tutorials/linux/ubuntu-postfix-gmail-smtp/)):

	sudo apt-get install postfix mailutils libsasl2-2 ca-certificates libsasl2-modules
	sudo vi /etc/postfix/main.cf
	
Add the following lines at the end of the file leaving the current contents in place:

	relayhost = [smtp.gmail.com]:587
	smtp_sasl_auth_enable = yes
	smtp_sasl_password_maps = hash:/etc/postfix/sasl_passwd
	smtp_sasl_security_options = noanonymous
	smtp_tls_CAfile = /etc/postfix/cacert.pem
	smtp_use_tls = yes

Next, create the sasl_password file

	sudo vi /etc/postfix/sasl_passwd
	
The file should contain a modified version of the format below with your gmail credentials.  This also works with email hosted by Gmail for your domain:	
	[smtp.gmail.com]:587    youremail@gmail.com:YOURPASSHERE

Next, lock down the security on the file and install certificates

	sudo chmod 400 /etc/postfix/sasl_passwd
	sudo postmap /etc/postfix/sasl_passwd
	cat /etc/ssl/certs/Thawte_Premium_Server_CA.pem | sudo tee -a /etc/postfix/cacert.pem
	sudo /etc/init.d/postfix reload
	
Finally, use the mail command to send a test message to yourself:
	
	echo "Test mail from postfix" | mail -s "Test Postfix" YOUREMAIL@YOURDOMAIN.COM

## Installing ant and git
Jenkins needs git installed for the git plugins to work.  While Jenkins automatically installs its own ant for use in builds, it is often useful to have ant available at the command line to debug builds.  The following command will install both for you:

	apt-get install ant git

# Configuring Jenkins
Once Jenkins is installed, we have to do some initial configuration before building out the jobs.

## Configuring Jenkins Global Settings

This section walks through configuring non-plugin specific options under Manage Jenkins -> Configure Global Settings.

### Location

You should have a hostname assigned to your server which you will use in the URL to access Jenkins.  Enter the server's URL in the Jenkins URL field and enter the sysadmin's email address.  If you ever change the server's hostname, 

![Jenkins Settings - Location](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/setup/jenkins_setup-location.png)

## Installing Plugins

Use the following steps for each plugin listed under Plugin Descriptions below:

* Go to Manage Jenkins -> Manage Plugins
* Click the Available tab
* Search for the plugin and check the box to the left of the row
* Click Install without Restart
* Repeat
* When done installing plugins, check the box to restart Jenkins when jobs are idle to complete the installation
* Once Jenkins reloads, your plugins should be installed

### Plugin Descriptions
This section provides a quick overview of each plugin to be installed and what function they serve in the Cumulus CI process.  All plugins which are not listed below are either default Jenkins plugins or plugins which are automatically installed when installing plugins from the list below.

#### build-name-setter

This plugin allows you to override the build name (normally a number like #54) to a custom string.  This is used in the cumulus_feature, cumulus_uat, and cumulus_rel jobs to name builds based on the branch name passed as a parameter.

#### Console Column Plugin

This plugin allows you to add an icon to your views (lists of jobs in Jenkins and their status) listing providing a quick link to the console output of a job.  Since Force.com deployment jobs log their status to the console, this is often the most useful entry point to a build.

#### Description Column Plugin

This plugin allows you to add a column to your views showing the description field from the job.  This is useful to provide a quick overview of the job which is shown alongside the build status.

#### embeddable-build-status

This plugin provides a generated image you can link into the README file in your repository so you can display a build status badge.

#### Environment Injector Plugin

Allows for injecting variables into the environment of a script.  This is only used in the cumulus_dev_cinnamon_test job.  Thus, it could be excluded if you are not using Cinnamon in your CI environment.

#### GitHub API Plugin

This plugin provides the bulk of the integration with Github including managing credentials to access Github, 

#### Github Authentication plugin

This plugin provides a new security policy for Jenkins which uses Github OAuth to authenticate users and grant them permissions to jobs based upon access granted to them with Github.  We've found this an easier approach since all devs already have a GitHub account to access the repository.

#### Green Balls

A simple UI tweak to change the colors of the status indicator icons in Jenkins to green, yellow, and red instead of the more confusing blue and red used by default by Jenkins.  This plugin is not essential but highly recommended.

#### Jenkins Email Extension Plugin

A supercharged email plugin with support for sending HTML emails and using Jetty templates for the emails.  The templates can be customized to include custom links relevant to your process.  Currently, we only use the default html Jetty template which provides most of what we need.

#### Jenkins Job Configuration History Plugin

Adds a badge to a build when the Job's configuration has changed.  This is useful to identify build failures caused by a bad job configuration change.

#### Jenkins Parameterized Trigger plugin

Allows a parameterized job to pass its parameters to a child job.  This is used in the cumulus_uat job to pass the branch (or tag in this case) name to the cumulus_uat_cinnamon_deploy job and by cumulus_uat_cinnamon_deploy to pass the name to cumulus_uat_cinnamon_test.

### End Result

The following screenshot shows the plugins used by the project after they have been installed into your Jenkins instance.  At this point, we have not encountered any version specific issues with the configuration so you should be able to ignore version numbers and get the latest available.

![Jenkins Settings - Manage Plugins](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/setup/jenkins_plugins.png)

## Configuring Plugins
Some of the plugins used need to be configured in the global settings while others either require no configuration or are configured in each job.  This section walks through configuring the global settings on the plugins which need it.

All the configurations below are set in Manage Jenkins -> Configure System

### Ant

![Jenkins Settings - Ant](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/setup/jenkins_setup-ant.png)

### Jenkins Email Extension (emailext)

![Jenkins Settings - emailext](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/setup/jenkins_setup-emailext.png)

### Git

We need to tell Jenkins how to find the git binary.  Since we used the Ubuntu package to install git, this is simple: git

![Jenkins Settings - Git](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/setup/jenkins_setup-git.png)

### GitHub API

Jenkins sometimes takes actions in Github such as setting the build status on commits through the Github Commit API.  The GitHub API section sets the identity used by Jenkins when calling the Github API for such actions.

![Jenkins Settings - GitHub API](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/setup/jenkins_setup-git_plugin.png)

### GitHub Web Hook

Jenkins will automatically setup the webhooks in Github so you builds can automatically be triggered by commits.  The credentials setup in this section are also used by other plugins to talk to Github.

#### Creating an OAuth token in Github

You will need both the username and password for Github as well as an OAuth token to setup the credentials.  For Cumulus, we created a dedicated Github user to serve as our robot: mrbelvedere.  It is recommended to create a similar user for your projects so you can tell actions which were taken by automated jobs vs actions taken by developers (i.e. humans).

In the Github account you want to use for automated actions, go to Account Settings and click Applications.  Under Personal Access Tokens, click *Create new token* and enter a name (i.e. your Jenkins server hostname).  Copy and paste the token shown after saving:

![Github - Personal Access Tokens](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/setup/github-personal_access_tokens.png)

#### Configuring Credentials in Jenkins

Once you have the OAuth token, go to Manage Jenkins -> Configure Global Settings and find the GitHub Web Hook section.  Enter the username, password, and token then click the Test Credentials button.  If all goes well, you will see the text *Verified* below the OAuth token field.

![Jenkins Settings - Github Webhook](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/setup/jenkins_setup-github_webhook_auth.png)

## Configuring Jenkins Security

By default, Jenkins is open to any web visitor.  Obviously, you'll want to lock down your instance before you start plugging authentication credentials in for services such as Github.  You could use a different authentication strategy for Jenkins if you'd like such as the built in user database or LDAP integration.

1. Make sure you have already entered and tested the credentials to access Github under Manage Jenkins -> Configure Global Settings -> GitHub Web Hook.
2. Go to Manage Jenkins -> Global Security
3. Configure per the screenshot below.  The Admin User Names should be a comma separated list of the Github usernames who should have full admin rights in Jenkins.  Make sure to include yourself in the list.

![](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/setup/jenkins_setup-global_security.png)

### If you lock yourself out
While working with the global security, it is fairly easy to lock yourself out of your Jenkins instance.  Resolving this problem is as simple as doing the follwing:

1. Edit /var/lib/jenkins/config.xml
2. Change `<useSecurity>true</useSecurity>` to `<useSecurity>false</useSecurity>`
3. Restart Jenkins with `sudo service jenkins restart`

This change disables security allowing anyone to edit your instance.  Once restarted, access your instance and go to Manage Jenkins -> Global Security to re-enable security with the proper configuration.

## Setting up Python scripts
The CumulusCI process currently uses a small python script to handle the cumulus_dev_to_feature job.  To avoid conflict with the system python, we build a python virtualenv to install additional python plugins needed by the script.  The following commands should setup the environment:

    cd /var/lib/jenkins/workspace
    git clone https://github.com/SalesforceFoundation/CumulusCI.git
    apt-get install python-virtualenv
    virtualenv venv
    source venv/bin/activate
    easy_install PyGithub
    deactivate
    
# Next Steps

At this point, you should have a fully configured server running Jenkins with all the plugins necessary to implement the CumulusCI process.  Next up...

* [Configure Jobs](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/jobs/README.md)
* [Install and Configure mrbelvedere](http://salesforcefoundation.github.io/mrbelvedere/)
