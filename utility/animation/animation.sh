
set -e

typingspeed=10
shortpause=1
mediumpause=2
longpause=5
scrollspeed=800

ESC="\033"
RESET="$ESC[0m"
PS1="\n$ESC[34m$ $RESET"

slowtype="pv -qL $[$typingspeed+(-2 + RANDOM%5)]"

echo=/bin/echo

main(){
    intro
    repo_setup
    cci_project_init
    secretly_copy_files
    add_files_to_git
    run_flow
    secretly_deploy_from_other_repo
    retrieve_changes
    fake_populate_org
    extract_dataset_from_org
    switch_orgs
    change_qa_org_flow
    look_at_qa_org
    cleanup
    banner "Tada!"
}

prompt(){
    printf "$PS1"
}

faketype(){
    echo  "$1" | pv -qL $[$typingspeed+(-2 + RANDOM%5)]
}

comment (){
    command="# $1"
    /bin/sleep $shortpause
    prompt
    printf "$ESC[32m" 
    echo "$command" | $slowtype
    printf "$RESET"
    /bin/sleep $shortpause
} 

fakedo(){
    prompt
    faketype "$1"
}

typedo (){
    command=$1
    prompt
    echo $command | $slowtype
    /bin/sleep $longpause
    echo
    eval $command
}
  
pretend_interact (){
    echo -en $1
    echo -n " "
    /bin/sleep $longpause
    faketype $2 
    /bin/sleep $shortpause
    echo 
}

banner (){
    figlet -W $1
}

slowpage="pv -qL $scrollspeed"

intro(){
    banner "Welcome to the demo of CumulusCI"
    sleep $longpause
    clear
    banner "Let's make a project from scratch!"
    sleep $mediumpause
}

repo_setup(){
    typedo "mkdir Food-Bank"
    typedo "cd Food-Bank"
    typedo "git init"
}

cci_project_init(){
    pretend_interact "$ESC[34m# Project Info$RESET
    \nThe following prompts will collect general information about the project
    \n
    \nEnter the project name.  The name is usually the same as your repository name.
    \nNOTE: Do not use spaces in the project name!
    \n$ESC[1mProject Name$RESET [Project]: "   " Food-Bank"


    pretend_interact  "CumulusCI uses an unmanaged package as a container for your project's metadata.
    \nEnter the name of the package you want to use.
    \n$ESC[1mPackage Name$RESET [Project]:"     "Food-Bank"

    pretend_interact "\n$ESC[1mIs this a managed package project? [y/N]:$RESET " "N"

    pretend_interact "\n$ESC[1mSalesforce API Version [48.0]:$RESET "  " "

    pretend_interact "Salesforce metadata can be stored using Metadata API format or DX source format. Which do you want to use?
    \n$ESC[1mSource format$RESET (sfdx, mdapi) [sfdx]:"   "sdfx"

    pretend_interact "$ESC[34m # Extend Project$RESET
    \nCumulusCI makes it easy to build extensions of other projects configured for CumulusCI like Salesforce.org's NPSP and EDA.  If you are building an extension of another project using CumulusCI and have access to its Github repository, use this section to configure this project as an extension.
    \n$ESC[1mAre you extending another CumulusCI project such as NPSP or EDA?$RESET [y/N]: "   "  "

    pretend_interact "$ESC[34m # Git Configuration$RESET
    \n
    \nCumulusCI assumes your default branch is master, your feature branches are named feature/*, your beta release tags are named beta/*, and your release tags are release/*.  If you want to use a different branch/tag naming scheme, you can configure the overrides here.  Otherwise, just accept the defaults.
    $ESC[1mDefault Branch$RESET [master]: "  "  "

    pretend_interact "$ESC[1mFeature Branch Prefix$RESET [feature/]: "  " "

    pretend_interact "$ESC[1mBeta Tag Prefix$RESET [beta/]: "   " "

    pretend_interact "$ESC[1mRelease Tag Prefix$RESET [release/]: "   " "

    pretend_interact "$ESC[34m# Apex Tests Configuration$RESET
    \nThe CumulusCI Apex test runner uses a SOQL where clause to select which tests to run.  Enter the SOQL pattern to use to match test class names.
    $ESC[1mTest Name Match [%_TEST%]:$RESET" " "

    pretend_interact "$ESC[1mDo you want to check Apex code coverage when tests are run?$RESET [Y/n]:" "Y"

    pretend_interact "$ESC[1mMinimum code coverage percentage$RESET [75]:" "75" 

    echo -e "$ESC[32mYour project is now initialized for use with CumulusCI$RESET"
    echo
}

secretly_copy_files(){
    cp -r ../CCI-Food-Bank/* .
    cp -r ../CCI-Food-Bank/.gitignore .
    rm -rf force-app/* unpackaged

    cp ../cumulusci.yml cumulusci.yml
}

add_files_to_git(){
    typedo 'ls'
    typedo 'git add --all'
    typedo 'git status'
    typedo 'git commit -m "Initial Configuration for CumulusCI"'
}

run_flow(){
    typedo 'cci org list'
    typedo 'cci flow list' | $slowpage
    typedo 'cci flow info dev_org' 
    typedo 'cci flow run dev_org --org dev'
    typedo 'cci org default dev'
    fakedo 'cci org browser'
    comment "CCI would log you in to your dev scratch org in a web browser."
    comment "You could create Custom Objects and Fields for tracking Deliveries and Delivery Items in Salesforce Setup"
}

secretly_deploy_from_other_repo(){
    # deploy from another repo to simulate user edits
    pushd ../CCI-Food-Bank > ../pushd.log
    cci flow run dev_org > ../deploy.log
    cci task run load_dataset >> ../load.log
    popd > ../popd.log
}

retrieve_changes(){
    comment "Let's take a look at what changed."
    comment "We'll start by looking for a task that can summarize changes."
    comment "CCI can list all of its changes:"
    typedo "cci task list" | $slowpage
    comment "That's a lot. Let's use grep to search for something specific"
    typedo "cci task list | grep changes" | $slowpage 
    typedo "cci task info list_changes" | $slowpage
    typedo "cci task run list_changes"
    typedo 'cci task run retrieve_changes'
    typedo 'git status'
    typedo 'git add force-app'
    typedo 'git commit -m "Initial schema for delivery tracking"'
}

new_org(){
    comment "Let's delete the scratch org and show how a teammate could populate from the repo"
    typedo 'cci org scratch_delete dev'
    typedo 'cci flow run dev_org'

}


switch_orgs(){
    comment "Let's start working with a different org, as a qa person might"
    typedo 'cci org default qa'
    typedo 'cci flow run dev_org --org qa'
}

fake_populate_org(){
    comment "The captured Delivery__c and Delivery_Item__c objects are now in the org."
    comment "Now we could use the Salesforce UI to create some records."
    fakedo 'cci org browser'
    comment "Let's pull them down and use them as sample data."
}

extract_dataset_from_org(){
    typedo 'cci task info generate_dataset_mapping'
    typedo 'cci task run generate_dataset_mapping'
    typedo 'cci task run extract_dataset'
    typedo 'ls datasets'
    typedo 'cat datasets/sample.sql'
    sleep $mediumpause
    typedo 'git add datasets'
    typedo 'git commit -m "Add sample data"'
}

change_qa_org_flow(){
    typedo 'cci flow info qa_org'

    # -- Add extract_dataset task as step 3 in config_qa

    fakedo "vim"
    sleep $shortpause
    vim cumulusci.yml -c "source ../append_task_script.vim"
    typedo "git add cumulusci.yml"
    typedo "cci flow info qa_org"
}

look_at_qa_org(){
    typedo "cci flow run qa_org --org qa"
    comment  "The QA org now has the captured dataset loaded automatically!"
    comment "We could go look at it in a web browser"
    fakedo 'cci org browser'
}

cleanup(){
    typedo 'git commit -m "Created demo dataset and added to qa_org flow"'
    typedo "cci org scratch_delete dev"
    typedo "cci org scratch_delete qa"
}

main
