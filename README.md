# IMPORTANT: CumulusCI 2 Notice

Change is coming soon.  For the last 6 months, we've been building out CumulusCI 2 in the feature/2.0 branch of this repository.  The time has come to merge CumulusCI 2 into the master branch.  What does this mean?

* **Switch to legacy-1.0 branch for legacy use cases**: If you want to continue using the Ant based CumulusCI, it is recommended that you switch from using the master branch to using legacy-1.0 which will be the original master branch before merging the feature/2.0 branch.  You can start doing this today to prepare for the migration.

* **Backwards compatibility**: In theory, the feature/2.0 repository structure should be backwards compatible with the current master.  All the legacy Ant and Python scripts are in the same locations: `build` and `ci` while the new cumulusci code mostly lives under `cumulusci`.  However, we have not tested the legacy support of this structure.  If you are concerned, please switch to the legacy-1.0 branch.

* **Consider Upgrading to CumulusCI 2**: CumulusCI 2 is going to be our main development focus going forward.  It is a complete rewrite of CumulusCI in Python with a ton more power and flexibility coupled with an easier to configure and more portable user experience.  Check out the docs at http://cumulusci.readthedocs.io for more information about CumulusCI 2.

# CumulusCI CLI

CumulusCI now provides a command line interface.  The CLI is evolving and not all functions are available through it yet.  You can find out more information about the CLI at https://github.com/SalesforceFoundation/CumulusCI/tree/master/cli

# CumulusCI

If you are already familiar with [Github Flow](http://scottchacon.com/2011/08/31/github-flow.html) and just want to get up and running using this process in the Salesforce platform, follow these steps:

1. Copy the files from the template directory into your own project
2. Fill in the properties
3. In your package.xml, add the "fullName" element as a child of "Package", like this:

    ```   
    <fullName>YourPackageName</fullName>
    ```

4. Set up your CI server (Jenkins, Codeship,…)
5. Clone CumulusCI in your CI server
6. Set a CUMULUSCI_PATH environment variable in the CI server that points to your forked copy
7. Make a commit to a branch to test everything works!
