# Principles for Testing the Cumulus Framework and Snowfakery

## Goals

1. tests should execute code paths as similar to end-user code as possible (fidelity)
2. tests should run as fast as possible (velocity)
3. tests should run properly even when third-party services are down or unavailable (availability)

Thus, mocking/faking should be used sparingly (as they work against
the goal of fidelity) and should only to deal with challenges
of velocity and availability.

## VCR for the easy cases

For simple cases, a transformation to use VCR allows all three goals to
be simultaneously achieved. Now that we have VCR, we can take a test like this:

```python
class TestLicensePreflights:
    def test_license_preflight(self):
        task = create_task(GetAvailableLicenses, {})
        task._init_api = Mock()
        task._init_api.return_value.query.return_value = {
            "totalSize": 2,
            "records": [
                {"LicenseDefinitionKey": "TEST1"},
                {"LicenseDefinitionKey": "TEST2"},
            ],
        }
        task()

        task._init_api.return_value.query.assert_called_once_with(
            "SELECT LicenseDefinitionKey FROM UserLicense"
        )
        assert task.return_values == ["TEST1", "TEST2"]
```

And transform it into:

```python
    @pytest.mark.vcr()
    def test_license_preflight(self, create_task):
        task = create_task(GetAvailableLicenses, {})
        task()
        expected = set(["SFDC", "CLOUD_INTEGRATION_USER"])
        actual = set(task.return_values)
        assert not expected.difference(actual), task.return_values
```

This meets all three of our core goals, and also will:

a) run against real orgs, when requested to
b) run against pretend orgs, otherwise
c) document the real-life behaviour of the task
d) survive any reorganization of the internals of the task

The ability to run against real orgs is an important
confidence-building measure when working with an environment
that constantly changes like SAAS services.

Using our testing infrastructure, you do so like this:

```s
$ pytest -k test_license_preflight --org qa
```

### How it Works

What happens under the cover is that the `create_task` fixture knows whether
the test suite is being run against a real org or not. If so, it passes
an `sf_org` object connected to a real Salesforce org. If not, it passes
a fake `sf_org` which will emulate a `qa_org`.

In a perfect world, we would achieve a very high level of test coverage
when every fake/mock is turned "off" and all code is running against
real systems, just as we have high coverage when they are ruened on.

The code paths which one might expect to be inaccessible in this mode are
code for handling errors, service outages, latency and high scale.

All other code should run against _real_ services or faked services
interchangably, depending on the current step in the SDLC.

### Component Tests

One of the goals is to test our system as real users use it, which is why
we use high-level APIs like `task()` instead of low level ones like
`task._run_task()`

That said, a system as complicated as Cumulus Framework cannot be tested only
from the _end_ user's perspective. Cumulus Framework consists of many components.

The "users" of these components are programmers on our team, and they should
be well-tested, just as if they were documented external APIs.

For example, the YAML merge algorithm is a component. The XML manipulator is
a component. The package XML library SHOULD BE a component, etc. These should
have test cases that ensure that their interfaces do not accidentally change.

## The Hard Cases: The Awkward Squad

In the lingo of functional programmers, our tests doesn't deal with the
"awkward squad" of issues other tests need to deal with:

-   a variety of org shapes
-   error/exception conditions
-   mutable state (in the org)
-   delays, timestamps and other temporal aspects

"Old fashioned" data faking may be needed to deal with these. The rest
of this document outlines techninques for handling these hard cases.

### Org shapes

Cumulus Framework has testing infrastructure which can create custom
orgs for tests:

```
@pytest.mark.vcr()
@pytest.mark.org_shape("person_accounts", "config_person_accounts")
def test_some_person_account_feature(self):
    ...
```

This will run the `config_person_accounts` flow against the `person_accounts`
org shape and run the test in the context of that org. At least that's
the goal. This infrastructure has not been tested or used much yet (e.g. for
actual person accounts testing).

### Simulating Networking Errors with VCR

It is possible to simulate networking errors by hand-editing VCR files.
This pattern can be observed [here](https://github.com/SFDO-Tooling/CumulusCI/blob/35b07ebfa80170f6e0e9d8cabd3da75bf41d5d59/cumulusci/utils/salesforce/tests/test_count_sobjects.py#L23) and [here](https://github.com/SFDO-Tooling/CumulusCI/blob/e3ba7e8b542755b6395dbc895daee3d1ea3d11dc/cumulusci/utils/salesforce/tests/cassettes/ManualEdit_TestCountSObjects.test_count_sobjects__network_errors.yaml#L16).

### Service Connectors

Third party services (including Salesforce) should always be wrapped in Service Connector
abstractions.

These abstractions can be tested with Requests and VCR.

The overall business logic can be tested by injecting fakes for Service Connectors.

A client library like simple_salesforce or github3 is not necessarily a good service
connector abstraction, because they work at a protocol level and not a business logic
level. Two examples, from simple_salesforce:

1. We make heavy use of simple_salesforce.restful(), which tunnels MANY different types
   of requests through a single endpoint and is therefore hard to fake.

2. We make heavy use of simple_salesforce.query() which has the same problem.

Github3 is better, but arguably if we had started using it by wrapping it we'd be in a
better position to add other VCS regardless, so maybe we should just always wrap
client libraries by default. The case of Github3 is argably, but simple_salesforce
is not: the fact that we do all sorts of protocol-level things (passing URLs,
fiddling headers) is a clear giveawaay that we should have wrapped it.

#### Wrap Universal Interfaces

An abstraction like Salesforce.query() should be used for situations such as the
end-user passing queries to us to execute. We, internally, should always wrap
it in a business-logic layer.

For example, instead of:

```python
sf_org.query("SELECT LicenseDefinitionKey FROM UserLicense")
```

There should be:

```
sf_org.get_user_licenses()
```

The latter can be faked much more easily and scalably. Imagine if you are testing
a large component which calls `sf_org.query()` six (or six hundred!) times. You'll
need to use string matching (which is intrinsically fragile) to figure out which
return values to return for which call.

Between the benefits of simpler tests, cleaner code and easier replacement of abstractions,
ServiceConnectors will pay for themselves quickly.

## Summarized Do's and Don'ts

1. Use VCR when possible. Edit the VCR files if necessary to emulate networking failures.

2. Mocking should only be used for replacing ServiceConnectors, not for
   replacing business logic code.

3. URLs, header manipulations, etc. should only occur in ServiceConnectors
   and never business logic.

4. Tests should test user-visible logic OR component boundaries OR performance
   logic (e.g. caching) and never the control flow within algorithms.

5. Use "Universal Interfaces" like query languages and REST protocols only
   a) in ServiceConnectors or b) when the Universal Interface has been exposed
   to the end-user themselves, and therefore cannot be wrapped in business logic.
