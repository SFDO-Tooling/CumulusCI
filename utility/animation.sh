faketype(){
    echo  $1 | pv -qL $[10+(-2 + RANDOM%5)]
}

slowtype="pv -qL $[50+(-2 + RANDOM%5)]"

comment (){
    command="# $1"
    /bin/sleep 1
    echo 
    echo -en "$ "
    echo -en "\033[32m" 
    echo "$command" | $slowtype
    echo -en "\033[0m"
    /bin/sleep 1
} 

typedo (){
    command=$1
    printf "$ "
    echo -n $command | pv -qL $[50+(-2 + RANDOM%5)]
    /bin/sleep 5
    echo
    eval $command
}

pretend_cci_init (){
    echo -en $1
    /bin/echo -n " "
    /bin/sleep 2
    faketype $2 
    /bin/sleep 1
    echo 
}

comment "Welcome to the demo of CumulusCI"
comment "Let's check that CumulusCI is installed:"
typedo "cci"
comment "Let's get a repository to work with"
typedo "git clone https://github.com/SFDO-Tooling/CumulusCI-Test"
# git init ...faster for testing
typedo "cd CumulusCI-Test"
typedo "ls"
comment "Let's remove the cumulusci.yml file so we can recreate it"
typedo "rm cumulusci.yml"

comment "Okay, here we go:"
echo "$ cci project init"

pretend_cci_init "\033[34m# Project Info\033[0m
\nThe following prompts will collect general information about the project
\n
\nEnter the project name.  The name is usually the same as your repository name.
\nNOTE: Do not use spaces in the project name!
\n\033[1mProject Name\033[0m [Project]: "   " CumulusCI-Test"


pretend_cci_init  "CumulusCI uses an unmanaged package as a container for your project's metadata.
\nEnter the name of the package you want to use.
\n\033[1mPackage Name\033[0m [Project]:"     "ccitest"

pretend_cci_init "\n\033[1mIs this a managed package project? [y/N]:\033[0m " "N"

pretend_cci_init "\n\033[1mSalesforce API Version [48.0]:\033[0m "  " "

pretend_cci_init "Salesforce metadata can be stored using Metadata API format or DX source format. Which do you want to use?
\n\033[1mSource format\033[0m (sfdx, mdapi) [sfdx]:"   "mdapi"

pretend_cci_init "\033[34m # Extend Project\033[0m
\nCumulusCI makes it easy to build extensions of other projects configured for CumulusCI like Salesforce.org's NPSP and EDA.  If you are building an extension of another project using CumulusCI and have access to its Github repository, use this section to configure this project as an extension.
\n\033[1mAre you extending another CumulusCI project such as NPSP or EDA?\033[0m [y/N]: "   "  "

pretend_cci_init "\033[34m # Git Configuration\033[0m
\n
\nCumulusCI assumes your default branch is master, your feature branches are named feature/*, your beta release tags are named beta/*, and your release tags are release/*.  If you want to use a different branch/tag naming scheme, you can configure the overrides here.  Otherwise, just accept the defaults.
\033[1mDefault Branch\033[0m [master]: "  "  "

pretend_cci_init "\033[1mFeature Branch Prefix\033[0m [feature/]: "  " "

pretend_cci_init "\033[1mBeta Tag Prefix\033[0m [beta/]: "   " "

pretend_cci_init "\033[1mRelease Tag Prefix\033[0m [release/]: "   " "

pretend_cci_init "\033[34m# Apex Tests Configuration\033[0m
\nThe CumulusCI Apex test runner uses a SOQL where clause to select which tests to run.  Enter the SOQL pattern to use to match test class names.
\033[1mTest Name Match [%_TEST%]:\033[0m" " "

pretend_cci_init "\033[1mDo you want to check Apex code coverage when tests are run?\033[0m [Y/n]:" "Y"

pretend_cci_init "\033[1mMinimum code coverage percentage\033[0m [75]:" "85" 

echo -e "\033[32mYour project is now initialized for use with CumulusCI\033[0m"
echo

echo -e "minimum_cumulusci_version: '3.13.2'
project:
    name: CumulusCI-Test
    package:
        name:  ccitest
        api_version: '48.0'
    source_format: mdapi

tasks:
    robot:
        options:
            suites: robot/CumulusCI-Test/tests
            options:
                outputdir: robot/CumulusCI-Test/results

    robot_testdoc:
        options:
            path: robot/CumulusCI-Test/tests
            output: robot/CumulusCI-Test/doc/CumulusCI-Test_tests.html

    run_tests:
        options:
            required_org_code_coverage_percent: 85" > cumulusci.yml


typedo "cat cumulusci.yml"
comment "We can add and commit our new cumulusci.yml to the git repository."
typedo "git add cumulusci.yml"
typedo 'git commit -m "Inititalized CumulusCI Configuration"'

comment "cci comes with some Saleforce Scratch org templates pre-configured"
typedo "cci org list"
comment "We can instantiate a Scratch org and look at its info like this:"
typedo "cci org info dev"
comment "Let's look at the org list again:"
typedo "cci org list"

comment "To make life easier, we can make our org the default org"
typedo "cci org default dev"

comment "### Tasks ###"

comment "Now we can look at tasks that CumulusCI has embedded."
comment "These tasks can be run against our org or any connected org."
typedo "cci task list"

comment "We can also learn more about a particular task:"
typedo "cci task info update_package_xml"
/bin/sleep 5

comment "Or we can run it"
typedo "cci task run update_package_xml"

comment "Tasks can take options, from the command line"
typedo "cci task run update_package_xml -o managed True -o output managed_package.xml"

comment "The update_package_xml task does not touch a Salesforce org. But most tasks do."
/bin/sleep 5
typedo "cci task run deploy"

comment "Now that the metadata is deployed, you can run the tests:"
typedo "cci task info run_tests"
/bin/sleep 5

typedo "cci task run run_tests"

comment "It is possible to write custom tasks in Python."

comment "### Flows ###"

comment "Flows are sequences of tasks."
comment "CumulusCI comes with a number of best-practice flows out of the box."

typedo "cci flow list"

comment "We can see the tasks in a flow"
typedo "cci flow info qa_org"

comment "And we can run a flow"
typedo "cci flow run qa_org"

comment "That flow configured an org for testing."
comment "Let's see what that it did in detail:"

typedo "cci task run list_changes"

comment "You can configure your own flows for any purpose."

comment  " ### Thank you for watching ### "
comment "Please give CumulusCI a try!"
