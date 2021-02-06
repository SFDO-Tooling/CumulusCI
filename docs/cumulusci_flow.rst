.. sectionauthor:: Jason Lantz <jlantz@salesforce.com>

==============
CumulusCI Flow
==============

CumulusCI Flow is the branching model and process we use for development of our products at Salesforce.org.  CumulusCI Flow is based on the Github Flow model with a few changes and additions.  One of the most common questions I'm asked by new developers joining our team is “Why don't we use git-flow with a development and release branch?”.  Unfortunately, despite having good answers to the question, it often involves a longer discussion to make the point.  That's the motivation for this article explaining why we use CumulusCI Flow over Github Flow or git-flow.

CumulusCI Flow is implemented in the default flows provided by CumulusCI, but the approach to working with a Github repository does not require the use of CumulusCI.

.. image:: images/salesforce-org-process.png
   :scale: 50 %
   :alt: Salesforce.org Dev/Release Process Diagram

Unique Considerations for Salesforce Projects
=============================================

CumulusCI Flow was designed for Salesforce development projects which inject some unique considerations into finding the right branching model:

* You cannot re-cut a Salesforce managed package release with the same version as a prior release.  As a result, Git Tags are the best representation of our releases in a repository since they are a read only reference to the exact code we put into a given release.
* Most Salesforce managed package projects use Push Upgrades to keep all users of the package on the latest release.  This eliminates the need to consider supporting multiple past versions.
* Releasing managed packages has some overhead involved including manual checks by release managers to ensure nothing gets permanently locked into the package in a release.  As a result, true continuous delivery isn't an option.  Whether you're on a team that wants to deliver quickly—say in a two week sprint cycle—or at team that makes several larger releases a year, CumulusCI offers functionality to help cut releases for all products with any changes.

Feature Branches
================

Like Github Flow, CumulusCI Flow uses a simple main/feature branch model.  The main branch is the only permanent branch in the repository.  All development work (features and bug fixes) is done in feature branches prefixed with feature/.  All commits on all feature branches are tested concurrently by our CI app, MetaCI, though any CI app could be used for the same purpose.

Once a developer is done with a feature branch, they create a Pull Request to merge their branch into the main branch.  The Pull Review serves as the container for the following:

* **Code Review**: We use Github's built in review functionality for Pull Requests to conduct line by line code reviews
* **Release Notes**: We use the Pull Request body to create release notes content relevant to the PR.  This content is automatically parsed by CumulusCI's release notes generation task to automatically build cumulative release notes on each release.
* **QA**: The goal of the Pull Request is to serve as a gate blocking a change from going into main until it's ready to release.  As a result, we do QA on the feature before merging the Pull Request.

When a Pull Request is approved and passing build, it is merged using the Merge button in Github's web interface.  We use Github Protected Branches to enforce both code reviews and passing builds before a Pull Request can be merged to main.

Once the Pull Request is merged, the feature branch is deleted.

Branch Configuration
--------------------
The name of the main (default) branch, as well as the branch prefixes are configurable in your projects ``cumulusci.yml`` file. The following shows the default values that CumulusCI comes with:

.. code-block:: yaml

   project:
      git:
         default_branch: main
         prefix_feature: feature/
         prefix_beta: beta/
         prefix_release: release/


Feature Branch Flows
--------------------

CumulusCI facilitates working with feature branches (mainly) through two default flows:

* **dev_org**: Used to deploy the unmanaged code and all dependencies from the feature branch into a Salesforce org to create a usable development environment.
* **ci_feature**: Deploys the unmanaged code and all dependencies into a Salesforce org (typically a fresh scratch org) and run the Apex tests.  This flow is typically run by your CI app on new commits to any feature branch.

Auto Merging
============
CumulusCI helps to keep large diffs and merge conflicts from being the norm. CumulusCI's auto-merge functionality helps teams:

   * Keep feature branches up-to-date with the ``main`` branch (main to feature merges)
   * Manage long-lived feature branches for larger features worked on by multiple developers (parent to child merges)
   * Manage large releases that occur several times a year (release to future release merges).  


Main to Feature Merges 
----------------------

One of the bigger differences between CumulusCI Flow and Github Flow or git-flow is that we automate the merging of commits to a projects main branch into all open feature branches.  This auto-merge does a lot for us:

* Ensures feature branches are in sync with the  main branch.
* Re-tests each feature branch with any changes to main since the merge generates a new commit
* Eliminates merge conflicts when merging a Pull Request to main

To understand the benefit of auto-merging to feature branches, consider the following scenario: A developer starts work on a feature branch, puts in a few weeks on it, and then has to leave unexpectedly for a few months.  While they are on leave, their feature branch gets automatically updated with any new commits on main and rebuilt.  A few weeks into their leave, a new commit on main gets merged to their feature branch and breaks the build.  When the developer returns after their leave, they can look at the build history to find which commit from main broke their feature branch.

Without auto-merging, the developer would return, merge main into their feature branch, and then have to sift through all the commits to main during their leave to figure out which one broke their feature branch.  More testing and build history is always a good thing in addition to the other benefits we gain from auto-merging.

CumulusCI facilitates the auto-merge to feature branches via the ``github_automerge_main`` task which is included by default in the ``release_beta`` flow.

Parent to Child Merges
----------------------

As we've worked in the CumulusCI Flow for the last 4+ years, we've occasionally seen the need for longer running, collaborative feature branches that are used by multiple developers to work on different parts of a single large feature. The solution was to expand the concept of auto-merging main-to-feature branches to also handle the concept of Parent and Child Feature Branches.

Parent/Child Feature Branches are created using a simple naming format for branches:

* **Parent**: feature/parent-branch-name
* **Child**: feature/parent-branch-name__child-branch-name

If this combination of named parent and child branches exist, the auto-merging functionality changes a bit:

* Child branches never receive the auto-merge from main
* Parent branches do receive the merge from main which kicks off a Feature Test build. (This assumes the parent branch is not itself a child.)
* At the end of a successful Feature Test build on a Parent branch, the parent branch is auto-merged into all child branches

This allows us to support multiple developers working on a single large feature while keeping that feature isolated from main until we're ready to release it. 
The parent branch is the branch representing the overall feature. Each developer can create child branches for individual components of the larger feature.  Their child branch still gets CI builds like all feature branches.  When they are ready to merge from their child branch to the parent branch, they create a Pull Request which gets code reviewed by other developers working on the parent feature branch and finally merged to the parent branch.

CumulusCI facilitates parent to child auto-merges via the `github_automerge_feature` task, which is included by deault in the `ci_feature` flow.  If a parent feature branch passes the build, it is automatically merged into all child branches.

The parent to child merge functionality works across multiple levels of branching. The effects of automerging remains the same, with children only receiving merges from their parents only (e.g. no merges from grandparents)
This allows us to have branching structures such as:

* ``main``
* ``feature/large-feature``
* ``feature/large-feature__section1``
* ``feature/large-feature__section1__work-item1``
* ``feature/large-feature__section1__work-item2``
* ``feature/large-feature__section2``
* ``feature/large-feature__section2__work-item1``

In this scenario, a commit to the ``main`` branch triggers the ``github_automerge_main`` task to run and will automerge that commit into ``feature/large-feature``.
This triggers a build to run against ``feature/large-feature``, and assuming the build passes, runs the ``github_automerge_feature`` task.
This task detects two child branches of ``feature/large-feature``; ``feature/large_feature__section1`` and ``feature/large-feature__section2``.
The task automerges the commit from the parent, into the child branches, and builds begin to run against those branches.
If the build for ``feature/large-feature__section1`` fails; then it would not trigger ``github_automerge_feature`` against it.
This means that despite ``feature/large-feature__section1`` having two child branches, they would not receive automerges.

You'll see see a great use case for this type of branching strategy in the next section.

Release Branches
----------------
Some teams deliver large releases several times a year.
For this type of release cadence, Salesforce.org uses a special type of branch referred to as a release branch. Release branches are simply a feature branch named with a number. These long-lived branches are created off of the ``main`` branch, serve as the target branch for all features associated with that release and are eventually merged back to the ``main`` branch when a release occurs.
To be able to clearly track what work is associated with a specific release, release branches adhere to the following:

* They are the parent branches of ALL feature work associated with a release. Put another way; all feature branches use the parent-child naming convention with its target release branch.
* Use a strict naming format: ``feature/release_num`` where ``release_num`` is a valid integer.

Using ``feature/`` branch prefix for the release branch names allow those branches to stay in sync with our main branch (they are just another feature branch to CumulusCI).
The release number immediately after the ``feature/`` prefix allows CumulusCI to perform yet another type of auto-merge for your convenience.

An example release branch with two items of work associated with it could look like this:

* ``feature/001``
* ``feature/001__feature1``
* ``feature/001__feature2``


Release to (Future) Release Merges
----------------------------------
Because release branches are so long-lived, and so much work goes into them, their diffs can get quite large.
This means headaches are inevitable the day after a major release, and you need to pull down all of the changes from the new release into the next release branch (which has likely been in development for months already).
To alleviate this pain point, CumulusCI can ensure that all commits made to the *lowest numbered* release branch are propagated to all other existing release branches.

Consider the following branches in a GitHub repository:

   * ``main`` - Source of Truth for Production
   * ``feature/002`` - The next major production release
   * ``feature/002__feature1`` - A single feature associated with release ``002``
   * ``feature/002__large_feature`` - A large feature associated with release ``002``
   * ``feature/002__large_feature__child1`` - First chunk of work for the large feature
   * ``feature/002__large_feature__child2`` - Second chunk of work for the large feature
   * ``feature/003`` - The release that comes after ``002``
   * ``feature/003__feature1`` - A single feature associated with release ``003``

In this scenario, CumulusCI ensures that when ``feature/002`` receives a commit, that that commit is also merged into ``feature/003``.
This kicks off tests in our CI system and ensures that funcitonality going into ``feature/002`` doesn't break work being done for future releases.
Once those tests pass, the commit on ``feature/003`` is merged to ``feature/003__feature1`` because they adhere to the parent/child naming convention described above.
Commits **never** propagate in the opposite direction. (A commit to ``feature/002`` would never be merged to ``feature/001`` if it was an existing branch in the GitHub repository).

**Propagating commits to future release branches is turned off by default.** 
If you would like to enable this feature for your GitHub repository, you can set the ``update_future_releases`` option on the ``github_automerge_feature`` task in your ``cumulusci.yml`` file: 

.. code-block:: yaml 

   tasks:
      github_automerge_feature:
      options:
         update_future_releases: True

Orphaned Branches
-----------------
If you have both a parent and a child branch, and the parent is deleted, this creates an orphaned branch.
Orphaned branches do not receive any auto-merges from any branches.
You can rename an orphaned branch to include the ``feature/`` prefix and contain no double underscores ('__') to begin receiving merges from the main branch again.

If we have a parent and child branch: ``feature/myFeature`` and ``feature/myFeature__child``, and ``feature/myFeature`` (the parent) is deleted, then ``feature/myFeature__child`` would be considered an orphan.
Renaming ``feature/myFeature__child`` to ``feature/child`` will allow the orphan to begin receiving automerges from the main branch.


Main Builds
=============

The main goal of the CumulusCI Flow is to always have the main branch ready to cut into a package.  This way, we can merge a fix and cut an emergency release at any time in the development process.

To test that we can package main, we upload a beta release on every commit to main and then test that beta release in a variety of Salesforce org environments concurrently.  This build ranges from 15 minutes to 2 hours depending on the project and a passing build is proof we can package main at any time.

When the upload of the beta release is completed, the main branch is auto-merged into all open feature branches.

New betas are published on Github as a Github Release along with automatically generated release notes created by parsing the body of all Pull Requests merged since the last production release

CumulusCI and Main Builds
---------------------------

CumulusCI facilitates the main builds mostly through four flows:

* **ci_master**: Deploys the main branch and all dependencies into the packaging org including incrementally deleting any metadata deleted in the commit.  The end result is a package that is ready to be uploaded from the packaging org.
* **release_beta**: Uploads a beta release of the code staged in the packaging org, creates a Github Tag and Release, generates release notes and adds to the release, and merges main to feature branches.
* **ci_beta**: Installs the beta and all dependencies into a fresh scratch org and runs the Apex tests.
* **ci_beta_install**: Installs the beta and all dependencies into a fresh scratch org. This is used to prepare environments for non-Apex testing such as automated browser tests.

Tag Naming Convention
=====================

CumulusCI Flow uses two naming conventions for the tags generated by the process:

* beta/1.2-Beta_3: Beta package releases
* release/1.2:  Production package releases

By differentiating beta and release tags, we allow tooling to query for the latest beta and the latest production release of each repository.

CumulusCI and Tag Naming Convention
-----------------------------------

CumulusCI's default tag prefixes can be overridden if needed for particular projects by setting the values under project -> git:

* **default_branch**: Override the default branch in the repository (default: ``main``, or the current branch during ``cci project init``)
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

When I first started figuring out our development/release process, I started where most people do in looking at git-flow.  Unlike both CumulusCI Flow and Github Flow, git-flow uses multiple permanent branches to separate development work from releases.  We decided to go with a main/feature branching model instead of git-flow for a few reasons:

* We only cut and release new releases.  We never patch old releases which makes the complexity of git-flow less necessary.
* git-flow is not natively supported in git or Github.  Using git-flow effectively usually requires extending your git tooling to enforce structure and merging rules for a more complex branching model.
* The main reason for git-flow is to be able to integrate your features together.  We get this, along with many other benefits, already from auto-merging main to feature branches.
* Feature branches provide better isolation necessary for a rapid, agile release cycle by keeping all features not ready for release out of the release.  Doing testing in the development branch means you've already integrated your features together.  If one feature is bad, it is harder to unwind that feature from the development branch than if it were still isolated in its feature branch, tested there, and only merged when truly ready.  Plus, with the auto-merge of main, we get the same integration as a development branch.
* In short, auto-merging and parent/child feature branches in CumulusCI Flow provide us everything we would want from git-flow in a simpler branching model.
