---
date: 2023-11-03
status: Accepted
author: "@jstvz"
---

<!--status: {proposed | rejected | accepted | deprecated | … | superseded by [ADR-0005](0005-example.md)}-->

# 2. Remove `robot_lint` task from CumulusCI

## Context and Problem Statement

We encountered a compatibility issue with the `robotframework-lint` library in CumulusCI when running on Python 3.12. This problem, coupled with the library's lack of recent activity and our need to support Python 3.12 soon, prompts a decision about our approach to linting within CumulusCI.

### Assumptions

-   Users who require linting functionality can install tools directly.
-   The majority of our users won't be critically affected by changes to the linting task.

### Constraints

-   We aim to minimize maintenance overhead for the CumulusCI team.
-   The solution should not introduce significant new dependencies or complications.

## Decision

### Considered Options

1. **Forking `robotframework-lint`**

    - **Pros**:
        - Direct control and maintenance of the library.
        - Ability to quickly address future issues or feature requests.
    - **Cons**:
        - Introduces maintenance overhead.
        - Uncertainty about the long-term activity or viability of the library.

2. **Vendoring the library**

    - **Pros**:
        - CumulusCI always ships with a working version.
        - No reliance on external repository maintenance.
    - **Cons**:
        - Challenges in updating the library.
        - Increases the project's size and complexity.

3. **Transitioning to [`robotframework-robocop`](https://github.com/MarketSquare/robotframework-robocop)**

    - **Pros**:
        - More active and potentially more feature-rich library.
        - Opportunity to benefit from community advancements.
    - **Cons**:
        - Introduces new dependencies.
        - Might not have exact parity with the current tool.
        - Requires rewriting `robot_lint` task.

4. **Complete removal of `robot_lint`**
    - **Pros**:
        - Simplifies CumulusCI's codebase.
        - Reduces maintenance overhead.
    - **Cons**:
        - Breaking change for users relying on the built-in task.
        - Users must handle their linting setups.

### Decision Outcome

**Completely remove `robot_lint`** from CumulusCI. Direct users who need linting functionality to install the necessary tool (`robotframework-lint` or `robotframework-robocop`) directly. This approach offers a cleaner and more maintainable path forward, even though it introduces a breaking change.

## Consequences

-   Users relying on the `robot_lint` task will need to adjust their setups. They'll need to directly install their linting tool of choice.
-   CumulusCI's codebase will be cleaner and easier to maintain without the additional linting task.
-   We'll need to communicate the change effectively to minimize disruption for users.

## References

-   [Slack discussion](https://salesforce-internal.slack.com/archives/G024TDY0P18/p1699034856029979)
-   [Issue highlighted by Stewart Anderson](https://github.com/boakley/robotframework-lint/issues/95)
-   [PR for the imp to importlib transition](https://github.com/boakley/robotframework-lint/pull/96)
