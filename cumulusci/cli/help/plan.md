# Plan Configuration

An installer is CumulusCI automation that is published to an instance of
MetaDeploy, such as install.salesforce.org, to be consumed directly by
customers in a “bring your own org” model. Installers are the primary
route through which we deliver the majority of our products.

An installer consists of three main components:

-   A CumulusCI flow that defines the automation.
-   Markup that defines the user experience of the installer.
-   Preflight checks that validate the target org.

## Definition of the plan's type, status, and location.

Installers are defined in a **_plans_** section in _cumulusci.yml_, which
allows you to specify metadata about the installer's user-facing
presentation, as well as specifying a flow you've implemented to provide
the automation. Here's an example of a plan's YAML markup from EDA:

```yaml
plans:
    install:
        slug: install
        title: Install
        tier: primary
        is_listed: True
        checks:
            - when: "not tasks.check_my_domain_active()"
              action: error
              message: "Please enable My Domain in your org prior to installing."
        steps:
            1:
                flow: customer_org
```

This plan has four main components:

1. **MetaDeploy metadata**
    - `slug` is the URL slug for the plan, e.g.,
      install.salesforce.org/products/eda/\<slug>.
    - `tier` is one of:
        - `primary` (limit: 1): The default plan most customers are expected to
          run. The primary plan should be install.
        - `secondary` (limit: 1): A plan is an alternate installation offered to the user.
        - `additional`: plans that deliver some additional support
          configurations or enable features after the customer has already
          installed the product.
    - `is_listed` defines whether or not this plan is visible to an end user who
      navigates to the product's landing page, defaults to `True`. **All
      published installers are accessible via direct link.**
2. **User-interface text.**: The `title`, `preflight_message`, `post_install_message`, and `error_message` keys are all part of messaging to the user.
3. **Preflight checks**: These checks are run before the plan begins to execute
   and can stop an installation if the org does not meet requirements, while
   presenting the user with appropriate messaging.
4. **Plan's `steps`**:Shown in the example as running the flow `customer_org`.
   While it's allowed for installers to have multiple steps (in fact, to define the
   entire plan automation here), we strongly encourage use of the `customer_org`
   pattern to allow installer automation to be consumed in many different contexts
   — including local runs with `cci flow run` and MetaCI builds using the Customer
   Org plan — and tested effectively. In this pattern, the only step in a plan is
   to invoke `customer_org`.

# User-Facing Step Names (`ui_options`)

In MetaDeploy, each step in an installer is presented to the user with a
friendly name: "Install NPSP 3.189", rather than `install_managed`.
These options, in most cases, come from `ui_options` markup that is
attached to the tasks that comprise the installer automation. Here's an
example:

```yaml
customer_org:
    steps:
        1:
            task: deploy_pre
            ui_options:
                record_types: # This is the name for a specific unpackaged/pre bundle
                    name: "Deploy Record Types"
        2:
            task: install_managed
            # No ui_options is required - this task generates its own.
        # More tasks
```

While you can, as shown here, include all of your `ui_options` directly
in the installer flow, it's also supported to decentralize the
`ui_options` into the tasks and flows that are composed to produce the
final installer. `ui_options` can be declared at the point of defining a
task, or in flows that are later composed into `customer_org` as well as
being consumed in other contexts:

```yaml
tasks:
    deploy_settings:
        class_path: cumulusci.tasks.apex.anon.AnonymousApexTask
        ui_options:
            name: Deploy Settings
        options:
            path: scripts/configure_settings.cls
            apex: initializeSettings();
```

Some tasks “freeze” into multiple MetaDeploy steps, like
`update_dependencies`, `deploy_pre`, and `deploy_post`, so `ui_options`
takes on a slightly different structure.

For `deploy_pre` and `deploy_post`, you can specify a name for each
bundle, using a nested structure (shown above) for each subdirectory.
`update_dependencies` freezes into multiple tasks per dependency, you
can number your `ui_options` to apply them to the whole sequence of
generated steps:

```yaml
task: update_dependencies
options:
    dependencies:
        - github: https://github.com/SalesforceFoundation/Cumulus
        - github: https://github.com/SalesforceFoundation/EDA
ui_options:
    1:
        name: NPSP - Account Record Types
    2:
        name: NPSP - Opportunity Record Types
    9:
        name: NPSP Config for Salesforce Mobile App
    10:
        name: EDA - Account Record Types
    11:
        name: EDA - Contact Key Affiliation Fields
    13:
        name: EDA - Deploy Case Behavior Record Types
    14:
        name: EDA - Deploy Course Connection Record Types
    15:
        name: EDA - Facility Display Name Formula Field
```

Here, installing NPSP and EDA generates a total of 15 or more steps.
Some of these steps, which install managed packages, automatically
generate a user-facing name. Others, which deploy unpackaged metadata,
require explicit configuration, here achieved by numbering the steps.
You can verify your steps match up by checking the output of the
`cci plan info` command.

# Preflight Checks

Preflight checks allow the installer to inspect the state of the org
prior to performing any changes, and then make decisions about which
tasks to run, whether to allow the installation to proceed, and whether
or not the user needs to view any warnings.

A preflight check has three components:

1.  `when`: an a Jinja2 template expression that evaluates to a
    `Boolean` value, `True` or `False`; for details consult the [Jinja2
    documentation][jinja_docs].
2.  `message`: text shown to the user if `when` evaluates to true.
3.  `action`: If `when` is `False`, do nothing. If `True`, perform the
    specified action.

`when` clauses may include:

-   a CumulusCI task, either custom or in the standard library, that
    returns data (`bool`, `str`, `dict`, etc) in its
    `self.return_values` property, or
-   a property called `org_config`, which contains data about the org's
    configuration, including values on the org's `Organization` sObject
    record.

Different values are allowed for `action`, depending on location:

-   Plans
    -   `error`: show `message` to the user and block installation
    -   `warn`: show `message` in a yellow toast-style banner
-   Tasks
    -   `hide`: the task is not shown or run
    -   `skip`: the task is shown, but not run
    -   `optional`: set `is_required` to `False`

Examples:

```yaml
- when: "not tasks.check_my_domain_active()"
  action: error
  message: "Please enable My Domain in your org prior to installing."
- when: "org_config.organization_sobject['SignupCountryIsoCode'] in ['BR','AR','CL']"
  action: warn
  message: "Some features may not be available in your country."
```

[jinja_docs]: https://jinja.palletsprojects.com/en/2.11.x/templates/#expressions
