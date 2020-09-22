FAQ
===

Why is it called CumulusCI?
  CumulusCI was originally created to power continuous integration (CI) for Cumulus, which was the code name for Salesforce.org's Nonprofit Success Pack. These days, it is used for many projects and supports activities beyond just CI, but the name has stuck.

Is CumulusCI hard to install?
  No. If you already have the Salesforce CLI installed and configured, installing CumulusCI for use across any project is a one-time process that takes 5-10 minutes.

Is CumulusCI specific to Salesforce.org or the nonprofit and education verticals?
  No. It is generic tooling and we aim to provide a best-practice process for anyone doing development on the Salesforce platform.

Is CumulusCI only for Open Source projects?
  No. Salesforce.org uses CumulusCI for both free, public Open Source products and for commercial managed package products developed in private GitHub repositories.

Is CumulusCI a replacement for the Salesforce CLI?
  No. CumulusCI builds on top of the commands provided by the Salesforce CLI and helps to manage and orchestrate them into a simple and straightforward user experience. CumulusCI prescribes a complete development, test, and release process out-of-the-box, while the Salesforce CLI is a lower level toolbelt that more agnostic to a particular process.

Does CumulusCI compete with Salesforce DX?
  No. CumulusCI shares a similar philosophy to Salesforce DX: the source of truth for a project should be in a version-controlled repository, and it should be as easy as possible to set up an org from scratch. CumulusCI uses the Salesforce CLI to perform certain operations such as creating scratch orgs, and is an alternative to bash scripts for running sequences of Salesforce CLI commands.

Do you need to know Python to use CumulusCI?
  No. While CumulusCI is written in Python, most CumulusCI users don't need to know Python, in the same way that most Salesforce DX users don't need to know Node.js.
