typingspeed=100
shortpause=0.1
mediumpause=0
longpause=0

slowtype="pv -qL $[$typingspeed+(-2 + RANDOM%5)]"

faketype(){
    echo  $1 | pv -qL $[$typingspeed+(-2 + RANDOM%5)]
}

comment (){
    command="# $1"
    /bin/sleep $shortpause
    echo 
    echo -en "$ "
    echo -en "\033[32m" 
    echo "$command" | $slowtype
    echo -en "\033[0m"
    /bin/sleep $shortpause
} 

typedo (){
    command=$1
    printf "$ "
    echo -n $command | $slowtype
    /bin/sleep $longpause
    echo
    eval $command
}

pretend_cci_init (){
    echo -en $1
    /bin/echo -n " "
    /bin/sleep $longpause
    faketype $2 
    /bin/sleep $shortpause
    echo 
}

banner (){
    figlet -W $1
}

slowpage (){
    pv -qL 700
}

banner "Welcome to the demo of CumulusCI"
sleep $longpause
clear
banner "Let's make a project from scratch!"
sleep $mediumpause

typedo "mkdir Food-bank"
typedo "cd Food-bank"
typedo "git init"

pretend_cci_init "\033[34m# Project Info\033[0m
\nThe following prompts will collect general information about the project
\n
\nEnter the project name.  The name is usually the same as your repository name.
\nNOTE: Do not use spaces in the project name!
\n\033[1mProject Name\033[0m [Project]: "   " Food-bank"


pretend_cci_init  "CumulusCI uses an unmanaged package as a container for your project's metadata.
\nEnter the name of the package you want to use.
\n\033[1mPackage Name\033[0m [Project]:"     "Food-bank"

pretend_cci_init "\n\033[1mIs this a managed package project? [y/N]:\033[0m " "N"

pretend_cci_init "\n\033[1mSalesforce API Version [48.0]:\033[0m "  " "

pretend_cci_init "Salesforce metadata can be stored using Metadata API format or DX source format. Which do you want to use?
\n\033[1mSource format\033[0m (sfdx, mdapi) [sfdx]:"   "sdfx"

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
    name: Food-bank
    package:
        name:  Food-bank
        api_version: '48.0'
    source_format: sfdx

tasks:
    robot:
        options:
            suites: robot/Food-bank/tests
            options:
                outputdir: robot/Food-bank/results

    robot_testdoc:
        options:
            path: robot/Food-bank/tests
            output: robot/Food-bank/doc/Food-bank_tests.html

    run_tests:
        options:
            required_org_code_coverage_percent: 75" > cumulusci.yml

typedo 'git add --all'
typedo 'git commit -m "Initial Configuration for CumulusCI"'

typedo 'cci org list'
typedo 'cci flow list' | slowpage
typedo 'cci flow info dev_org' 
typedo 'cci flow run dev_org --org dev'
typedo 'cci org default dev'
typedo 'cci org browser'

comment "CCI would log you in to your dev scratch org."
comment "You could create Custom Objects and Fields for tracking Deliveries and Delivery Items in Setup"
comment "Let's take a look at what changed."
typedo "cci task list" | slowpage
typedo "cci task info list_changes" | slowpage
typedo "cci task run list_changes"
typedo 'cci task run list_changes -o exclude "Profile: "'
# cci task run retrieve_changes -o eclude "Profile: "
# git status
# git add force-app
# git commit -m "Initial schema for delivery tracking"
# cci org scratch_delete dev
# cci flow run dev_org
# cci org browser
# # The captured Delivery__c and Delivery_Item__c objects are now in the org.  Create some records
# cci task info generate_dataset_mapping
# cci task run generate_dataset_mapping
# cci task run extract_dataset
# git status
# cat datasets/demo.sql
# git add datasets
# git commit
# cci flow info qa_org
# vim cumulusci.yml # echo multiline to cumulusci.yml if needed
# -- Add extract_dataset task as step 3 in config_qa
# cci flow info qa_org
# cci flow run qa_org --org qa
# cci org browser qa
# # The QA org now has the captured dataset loaded automatically!
# git commit -m "Created demo dataset and added to qa_org flow"
# cci org scratch_delete dev
# cci org scratch_delete qa
# FIN

# typedo "cci"
# comment "Let's get a repository to work with"
# typedo "git clone https://github.com/SFDO-Tooling/CumulusCI-Test"
# # git init ...faster for testing
# typedo "cd CumulusCI-Test"
# typedo "ls"
# comment "Let's remove the cumulusci.yml file so we can recreate it"
# typedo "rm cumulusci.yml"

# comment "Okay, here we go:"
# echo "$ cci project init"





# typedo "cat cumulusci.yml"
# comment "We can add and commit our new cumulusci.yml to the git repository."
# typedo "git add cumulusci.yml"
# typedo 'git commit -m "Inititalized CumulusCI Configuration"'

# comment "cci comes with some Saleforce Scratch org templates pre-configured"
# typedo "cci org list"
# comment "We can instantiate a Scratch org and look at its info like this:"
# typedo "cci org info dev"
# comment "Let's look at the org list again:"
# typedo "cci org list"

# comment "To make life easier, we can make our org the default org"
# typedo "cci org default dev"

# comment "### Tasks ###"

# comment "Now we can look at tasks that CumulusCI has embedded."
# comment "These tasks can be run against our org or any connected org."
# typedo "cci task list"

# comment "We can also learn more about a particular task:"
# typedo "cci task info deploy"
# /bin/sleep 5

# comment "Or we can run it"
# typedo "cci task run deploy"

# comment "Now that the metadata is deployed, you can run the tests:"
# typedo "cci task info run_tests"
# /bin/sleep 5

# typedo "cci task run run_tests"

# comment "We can also specify options for tests."
# comment "First let's see what options are available:"

# typedo "cci task info run_tests"
# /bin/sleep 5

# comment "Let's run just a single test"
# typedo "cci task run run_tests -o test_name_match SamplePage_CTRL_TEST"

# comment "It is possible to write custom tasks in Python, but we won't teach that today."

# comment "Instead, let's look at Flows."

# comment "### Flows ###"

# comment "Flows are sequences of tasks."
# comment "CumulusCI comes with a number of best-practice flows out of the box."

# typedo "cci flow list"

# comment "We can see the tasks in a flow"
# typedo "cci flow info qa_org"

# comment "And we can run a flow"
# typedo "cci flow run qa_org"

# comment "That flow configured an org for testing."
# comment "Let's see what that it did in detail:"

# typedo "cci task run list_changes"

# comment "You can configure your own flows for any purpose."

# comment  " ### Thank you for watching ### "
# comment "Please give CumulusCI a try!"
