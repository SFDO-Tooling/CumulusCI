# GithubReleaseNotesGenerator

This task generates release notes by finding all merged pull requests to the default branch between the date two tags were created.

When you create Pull Requests against the default branch, the generator will parse the Pull Request's body for content that should be included in release notes.

## Critical Changes

The Critical Changes section is where you should list off any changes which might impact existing functionality.

Start the section with `# Critical Changes` followed by your content

For example:

    This won't be included
    
    # Critical Changes
    
    This will be included in Critical Changes
    
## Changes

The Changes section is where you should list off any changes worth highlight to users in the release notes.  This section should always include instructions for users for any post-upgrade tasks they need to perform to enable new functionality.  For example, users should be told to grant permissions and add new CustomFields to layouts.

Start the section with `# Changes` followed by your content

For example:

    This won't be included
    
    # Changes
    
    This will be included in Changes
    
## Issues Closed

The Issues Closed section is where you should link to any closed issues that should be listed in the release notes.

Start the section with `# Changes` followed by your content

For example:

    This won't be included
    
    # Issues Closed
    
    Fixes #102
    resolves #100
    This release closes #101

Would output:

    # Issues Closed

    #100: Title of Issue 100
    #101: Title of Issue 101
    #102: Title of Issue 102
    
A few notes about how issues are parsed:

* The parser uses the same format as Github: https://help.github.com/articles/closing-issues-via-commit-messages/
* The parser searches for all issue numbers and sorts them by their integer value, looks up their title, and outputs a formatted line with the issue number and title for each issue.
* The parser ignores everything else in the line that is not an issue number.  Anything that is not an issue number will not appear in the rendered release notes
