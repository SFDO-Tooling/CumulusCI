.. sectionauthor:: Jason Lantz <jlantz@salesforce.com>
==============
CumulusCI Flow
==============

CumulusCI Flow is the branching model and process we use for development of our products at Salesforce.org.  CumulusCI Flow is based on the Github Flow model with a few changes and additions.  One of the most common questions I'm asked by new developers joining our team is “Why don't we use git-flow with a development and release branch?”.  Unfortunately, despite having good answers to the question, it often involves a longer discussion to make the point.  That's the motivation for this article explaining why we use CumulusCI Flow over Github Flow or git-flow.

CumulusCI Flow is implemented in the default flows provided by CumulusCI, but the approach to working with a Github repository does not require the use of CumulusCI.

Unique Considerations for Salesforce Projects
=============================================

CumulusCI Flow was designed for Salesforce development projects which inject some unique considerations into finding the right branching model:

* You cannot re-cut a Salesforce managed package release with the same version as a prior release.  As a result, Git Tags are the best representation of our releases in a repository since they are a read only reference to the exact code we put into a given release.
* Most Salesforce managed package projects use Push Upgrades to keep all users of the package on the latest release.  This eliminates the need to consider supporting multiple past versions.
* Releasing managed packages has some overhead involved including manual checks by release managers to ensure nothing gets permanently locked into the package in a release.  As a result, true continuous delivery isn't an option.  We work in 2 week sprints and cut releases at the end of each sprint for all products with any changes.

Feature Branches
================

Like Github Flow, CumulusCI Flow uses a simple master/feature branch model.  The master branch is the only permanent branch in the repository.  All development work (features and bug fixes) is done in feature branches prefixed with feature/.  All commits on all feature branches are tested concurrently by our CI app, MetaCI, though any CI app could be used for the same purpose.

Once a developer is done with a feature branch, they create a Pull Request to merge their branch into the master branch.  The Pull Review serves as the container for the following:

* **Code Review**: We use Github's built in review functionality for Pull Requests to conduct line by line code reviews
* **Release Notes**: We use the Pull Request body to create release notes content relevant to the PR.  This content is automatically parsed by CumulusCI's release notes generation task to automatically build cumulative release notes on each release.
* **QA**: The goal of the Pull Request is to serve as a gate blocking a change from going into master until it's ready to release.  As a result, we do QA on the feature before merging the Pull Request.

When a Pull Request is approved and passing build, it is merged using the Merge button in Github's web interface.  We use Github Protected Branches to enforce both code reviews and passing builds before a Pull Request can be merged to master.

Once the Pull Request is merged, the feature branch is deleted.

CumulusCI and Feature Branches
------------------------------

CumulusCI facilitates working with feature branches mostly via two default flows:

* **dev_org**: Used to deploy the unmanaged code and all dependencies from the feature branch into a Salesforce org to create a usable development environment.
* **ci_feature**: Deploys the unmanaged code and all dependencies into a Salesforce org (typically a fresh scratch org) and run the Apex tests.  This flow is typically run by your CI app on new commits to any feature branch.

Auto-Merging Master to Feature Branches
=======================================

One of the bigger differences between CumulusCI Flow and Github Flow or git-flow is that we automate the merging of master commits into all open feature branches the initial master build passes.  This auto-merge does a lot for us:

* Ensures feature branches always track with master
* Re-tests each feature branch with any changes to master since the merge generates a new commit
* Eliminates merge conflicts when merging a Pull Request to master

To understand the benefit of auto-merging to feature branches, consider the following scenario: A developer starts work on a feature branch, puts in a few weeks on it, and then has to leave unexpectedly for a few months.  While they are on leave, their feature branch gets automatically updated with any new commits on master and rebuilt.  A few weeks into their leave, a new commit on master gets merged to their feature branch and breaks the build.  When the developer returns after their leave, they can look at the build history to find which commit from master broke their feature branch.

Without auto-merging, the developer would return, merge master into their feature branch, and then have to sift through all the commits to master during their leave to figure out which one broke their feature branch.  More testing and build history is always a good thing in addition to the other benefits we gain from auto-merging.

CumulusCI and Auto-Merging to Feature Branches
----------------------------------------------

CumulusCI facilitates the auto-merge to feature branches via the task `github_master_to_feature` which is included by default in the `release_beta` flow run to publish a beta release.

Parent/Child Feature Branches
=============================

As we've worked in the CumulusCI Flow for the last 4+ years, we started to see a need for longer running, collaborative feature branches used by multiple developers to work on different parts of a bigger feature.  The solution was to expand the concept of auto-merging master to feature branches to also handle the concept of Parent/Child Feature Branches.

Parent/Child Feature Branches are created using a simple naming format for branches:

* **Parent**: feature/parent-branch-name
* **Child**: feature/parent-branch-name__child-branch-name

If this combination of named parent and child branches exist, the auto-merging functionality changes a bit:

* Child branches never receive the auto-merge from master
* Parent branches do receive the merge from master which kicks off a Feature Test build
* At the end of a successful Feature Test build on a Parent branch, the parent branch is auto-merged into all child branches

This allows us to support multiple developers working on one big feature while keeping the whole feature isolated from master until we're ready to release it.  The parent branch is the branch representing the overall feature.  Each developer can create child branches for individual components of the larger feature.  Their child branch still gets CI builds like all feature branches.  When they are ready to merge from their child branch to the parent branch, they create a Pull Request which gets code reviewed by other developers working on the parent feature branch and finally merged to the parent branch.

CumulusCI and Parent/Child Feature Branches
-------------------------------------------

CumulusCI facilitates the auto-merge to feature branches via the task `github_parent_to_children` which is included by deault in the `ci_feature` flow.  If a parent feature branch passes the build, it is automatically merged into all child branches.

Master Builds
=============

The main goal of the CumulusCI Flow is to always have the master branch ready to cut into a package.  This way, we can merge a fix and cut an emergency release at any time in the development process.

To test that we can package master, we upload a beta release on every commit to master and then test that beta release in a variety of Salesforce org environments concurrently.  This build ranges from 15 minutes to 2 hours depending on the project and a passing build is proof we can package master at any time.

When the upload of the beta release is completed, the master branch is auto-merged into all open feature branches.

New betas are published on Github as a Github Release along with automatically generated release notes created by parsing the body of all Pull Requests merged since the last production release

CumulusCI and Master Builds
---------------------------

CumulusCI facilitates the master builds mostly through four flows:

* **ci_master**: Deploys the master branch and all dependencies into the packaging org including incrementally deleting any metadata deleted in the commit.  The end result is a package that is ready to be uploaded from the packaging org.
* **release_beta**: Uploads a beta release of the code staged in the packaging org, creates a Github Tag and Release, generates release notes and adds to the release, and merges master to feature branches.
* **ci_beta**: Installs the beta and all dependencies into a fresh scratch org and runs the Apex tests.
* **ci_beta_install**: Installs the beta and all dependencies into a fresh scratch org.  This is used to prepare environments for non-Apex testing such as automated browser tests.

Tag Naming Convention
=====================

CumulusCI Flow uses two naming conventions for the tags generated by the process:

* beta/1.2-Beta_3: Beta package releases
* release/1.2:  Production package releases

By differentiating beta and release tags, we allow tooling to query for the latest beta and the latest production release of each repository.

CumulusCI and Tag Naming Convention
-----------------------------------

CumulusCI's default tag prefixes can be overridden if needed for particular projects by setting the values under project -> git:

* **default_branch**: Override the default branch in the repository (default: master)
* **prefix_beta**: Override the prefix for beta tags (default: beta/)
* **prefix_feature**: Override the prefix for feature branches (default: feature/)
* **prefix_release**: Override the prefix for release tags (default: release/)


CumulusCI Flow vs Github Flow
=============================

Since CumulusCI Flow is largely an extension of Github Flow, the differences are mostly additional process in CumulusCI Flow that's not in Github Flow:

* Feature branches must be prefixed feature/ or they don't get built or receive auto-merges.  This allows developers to have experimental branches that don't get built or merged.
* CumulusCI Flow is focused on an agile release process (we use 2 week sprints/releases) instead of continuous delivery.
* CumulusCI Flow requires the beta and release tag naming convention so tooling can use the Github API to determine the latest beta and the latest production release.
* Github Flow does not do any auto-merging of commits which is a core part of CumulusCI Flow
* Github Flow does not have any concept of parent/child branches though they could be manually created and maintained

CumulusCI Flow vs git-flow
==========================

When I first started figuring out our development/release process, I started where most people do in looking at git-flow.  Unlike both CumulusCI Flow and Github Flow, git-flow uses multiple permanent branches to separate development work from releases.  We decided to go with a master/feature branching model instead of git-flow for a few reasons:

* We only cut and release new releases.  We never patch old releases which makes the complexity of git-flow less necessary.
* git-flow is not natively supported in git or Github.  Using git-flow effectively usually requires extending your git tooling to enforce structure and merging rules for a more complex branching model.
* The main reason for git-flow is to be able to integrate your features together.  We get this, along with many other benefits, already from auto-merging master to feature branches.
* Feature branches provide better isolation necessary for a rapid, agile release cycle by keeping all features not ready for release out of the release.  Doing testing in the development branch means you've already integrated your features together.  If one feature is bad, it is harder to unwind that feature from the development branch than if it were still isolated in its feature branch, tested there, and only merged when truly ready.  Plus, with the auto-merge of master, we get the same integration as a development branch.
* In short, auto-merging and parent/child feature branches in CumulusCI Flow provide us everything we would want from git-flow in a simpler branching model.
