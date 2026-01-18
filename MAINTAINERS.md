# Maintainers Runbook

This document provides guidance for maintainers of Clariti CumulusCI.

## Table of Contents

-   [Version Management](#version-management)
-   [Python Version Requirements](#python-version-requirements)
-   [Release Process](#release-process)
-   [Syncing with Upstream](#syncing-with-upstream)
-   [Key Files Reference](#key-files-reference)
-   [Common Maintenance Tasks](#common-maintenance-tasks)

---

## Version Management

### Bumping the Version

The version is stored in a single source of truth:

```
cumulusci/__about__.py
```

To bump the version:

```bash
# Using hatch (recommended)
hatch version minor    # 4.6.0 -> 4.7.0
hatch version patch    # 4.6.0 -> 4.6.1
hatch version major    # 4.6.0 -> 5.0.0
hatch version dev      # 4.6.0 -> 4.6.0.dev1
hatch version beta     # 4.6.0 -> 4.6.0b1

# Or manually edit
# cumulusci/__about__.py: __version__ = "4.7.0"
```

### Version Format

We follow semantic versioning with optional pre-release tags:

-   **Release**: `4.6.0`
-   **Development**: `4.6.0.dev1`
-   **Beta**: `4.6.0b1`
-   **Alpha**: `4.6.0a1`
-   **Release Candidate**: `4.6.0rc1`

---

## Python Version Requirements

When changing the minimum Python version, update **ALL** of these locations:

### Files to Update

| File                      | Location | Current Value                           |
| ------------------------- | -------- | --------------------------------------- |
| `pyproject.toml`          | Line 10  | `requires-python = ">=3.11"`            |
| `cumulusci/__init__.py`   | Line 26  | `sys.version_info < (3, 11)`            |
| `cumulusci/cli/utils.py`  | Line 18  | `LOWEST_SUPPORTED_VERSION = (3, 11, 0)` |
| `cumulusci/cli/utils.py`  | Line 108 | Error message mentioning Python version |
| `docs/get-started.md`     | Line 72  | Python download instructions            |
| `.github/workflows/*.yml` | Various  | `python-version` in matrix              |

### Checklist for Python Version Bump

```bash
# 1. Update pyproject.toml
sed -i '' 's/requires-python = ">=3.11"/requires-python = ">=3.12"/' pyproject.toml

# 2. Update __init__.py version check
# Edit cumulusci/__init__.py line 26

# 3. Update cli/utils.py constants
# Edit cumulusci/cli/utils.py lines 18 and 108

# 4. Update docs
# Edit docs/get-started.md

# 5. Update CI matrix in workflows
# Edit .github/workflows/feature_test.yml

# 6. Verify changes
grep -r "3\.11" --include="*.py" --include="*.toml" --include="*.yml" --include="*.md" | grep -v history.md
```

---

## Release Process

### Pre-Release Checklist

1. [ ] All tests passing on main branch
2. [ ] Version bumped appropriately
3. [ ] Changelog updated in `docs/history.md`
4. [ ] Documentation builds successfully

### CI-Based Release (Recommended)

The recommended way to release is using GitHub Actions workflows:

#### 1. Trigger the Pre-Release Workflow

Go to **Actions** → **Draft release pull request** → **Run workflow**

-   Select version bump type: `major`, `minor`, `patch`, `dev`, `alpha`, `beta`, `preview`
-   This automatically:
    -   Bumps the version in `cumulusci/__about__.py`
    -   Generates changelog from GitHub PRs/commits
    -   Creates a release PR

#### 2. Review and Merge the PR

-   Review the auto-generated changelog in `docs/history.md`
-   Make any manual edits if needed
-   Merge the PR to `main`

#### 3. Automatic Publishing

Once merged, the `release.yml` workflow automatically:

-   Builds the package (`hatch build`)
-   Publishes to PyPI (`hatch publish`)
-   Creates a GitHub Release with changelog and artifacts

**Workflow Files:**

-   `.github/workflows/pre-release.yml` - Creates release PR
-   `.github/workflows/release.yml` - Publishes on merge

**PyPI Trusted Publishing Setup:**

No API tokens needed! Uses OIDC authentication. The workflow automatically selects the environment based on version:

| Version Pattern      | Example               | Environment   | GitHub Release |
| -------------------- | --------------------- | ------------- | -------------- |
| `*.dev*`             | `4.6.0.dev2`          | `development` | Pre-release    |
| `*a*`, `*b*`, `*rc*` | `4.6.0b1`, `4.6.0rc1` | `staging`     | Pre-release    |
| Final                | `4.6.0`               | `production`  | Release        |

**Configure Trusted Publishers in PyPI:**

Go to https://pypi.org/manage/project/clariti-cumulusci/settings/publishing/ and add:

| Environment   | Owner             | Repository  | Workflow      |
| ------------- | ----------------- | ----------- | ------------- |
| `development` | `ClaritiSoftware` | `CumulusCI` | `release.yml` |
| `staging`     | `ClaritiSoftware` | `CumulusCI` | `release.yml` |
| `production`  | `ClaritiSoftware` | `CumulusCI` | `release.yml` |

**Note:** Create matching GitHub environments in repo Settings → Environments. Production can require approval.

---

### Manual Release (Fallback)

Use this if CI is unavailable or for emergency releases.

#### Creating a Release

```bash
# 1. Ensure you're on main and up to date
git checkout main
git pull origin main

# 2. Run tests
make test

# 3. Create release branch
git checkout -b release-v4.7.0

# 4. Bump version
hatch version minor

# 5. Update changelog in docs/history.md

# 6. Commit and push
git add -A
git commit -m "TICKET-XXX release: v4.7.0"
git push origin release-v4.7.0

# 7. Create PR and merge to main
```

#### Publishing to PyPI

```bash
# Build the package
hatch build

# Publish to PyPI (will prompt for credentials if not configured)
hatch publish

# Or using twine (alternative)
# pip install twine
# twine check dist/*
# twine upload dist/*
```

### Dev Release (Pre-release)

```bash
# Bump to next dev version
hatch version dev      # e.g., 4.6.0.dev1 -> 4.6.0.dev2

# Update changelog in docs/history.md

# Commit
git add -A && git commit -m "TICKET-XXX release: bump version to vX.X.X.devX with changelog"

# Build and publish
hatch build && hatch publish
```

---

## Syncing with Upstream

### Adding Upstream Remote

```bash
git remote add upstream https://github.com/SFDO-Tooling/CumulusCI.git
git fetch upstream
```

### Merging Upstream Changes

```bash
# 1. Fetch upstream
git fetch upstream

# 2. Create a sync branch
git checkout -b sync-upstream-YYYY-MM-DD

# 3. Merge upstream main
git merge upstream/main

# 4. Resolve conflicts (prioritize our changes for rebranded files)
# Key files to keep ours:
#   - pyproject.toml (package name, author, URLs)
#   - README.md
#   - LICENSE (keep both copyrights)
#   - docs/conf.py
#   - cumulusci/cli/utils.py (PyPI URL)
#   - cumulusci/utils/__init__.py (upgrade commands)

# 5. Test
make test

# 6. Push and create PR
git push origin sync-upstream-YYYY-MM-DD
```

### Conflict Resolution Priority

| File Category                                    | Resolution                                 |
| ------------------------------------------------ | ------------------------------------------ |
| Branding files (README, LICENSE, pyproject.toml) | Keep ours                                  |
| Documentation URLs                               | Keep ours (claritisoftware.github.io)      |
| Core functionality                               | Merge carefully, prefer upstream bug fixes |
| New features from upstream                       | Accept if compatible                       |
| CI/CD workflows                                  | Review case by case                        |

---

## Key Files Reference

### Package Metadata

| File                     | Purpose                                       |
| ------------------------ | --------------------------------------------- |
| `pyproject.toml`         | Package configuration, dependencies, metadata |
| `cumulusci/__about__.py` | Version string (single source of truth)       |
| `cumulusci/__init__.py`  | Package initialization, version export        |

### Branding & Legal

| File          | Purpose                              |
| ------------- | ------------------------------------ |
| `README.md`   | Main project documentation           |
| `LICENSE`     | BSD 3-Clause license with copyrights |
| `LEGAL.md`    | Legal compliance documentation       |
| `AUTHORS.rst` | Contributors list                    |

### CLI & User-Facing

| File                          | Purpose                            |
| ----------------------------- | ---------------------------------- |
| `cumulusci/cli/utils.py`      | Version checking, upgrade commands |
| `cumulusci/cli/error.py`      | Error help URLs                    |
| `cumulusci/utils/__init__.py` | PIP/PIPX upgrade command strings   |

### Documentation

| File                   | Purpose                   |
| ---------------------- | ------------------------- |
| `docs/conf.py`         | Sphinx configuration      |
| `docs/get-started.md`  | Installation instructions |
| `docs/contributing.md` | Contribution guidelines   |

### CI/CD

| File                                 | Purpose                  |
| ------------------------------------ | ------------------------ |
| `.github/workflows/feature_test.yml` | Main CI workflow         |
| `.github/workflows/docs.yml`         | Documentation deployment |
| `.github/workflows/pre-release.yml`  | Release automation       |
| `.github/CODEOWNERS`                 | Code review assignments  |

---

## Common Maintenance Tasks

### Adding a New Dependency

```bash
# 1. Add to pyproject.toml under [project.dependencies]

# 2. Regenerate lock file
uv lock

# 3. Test
uv sync && make test

# 4. Check license compatibility (see LEGAL.md)
```

### Updating Documentation URLs

If documentation hosting changes, update:

```bash
grep -r "claritisoftware.github.io/CumulusCI" --include="*.py" --include="*.md" --include="*.yml"
```

### Regenerating Schema

```bash
make schema
```

### Running Full Test Suite

```bash
# Unit tests
make test

# With coverage
make coverage

# Lint
make lint

# Build docs
make docs
```

### Testing GitHub Actions Locally

```bash
# Using the workflow runner (requires act)
make workflow-test WORKFLOW=feature_test

# Or using Python script
python scripts/run_workflow.py feature_test --dry-run
```

---

## Emergency Procedures

### Reverting a Bad Release

```bash
# 1. Yank from PyPI (use web interface)
#    Go to https://pypi.org/manage/project/clariti-cumulusci/releases/
#    Select the version and click "Yank" (hides but doesn't delete)

# 2. Create hotfix
git checkout -b hotfix-v4.7.1
# Fix the issue
hatch version patch
git add -A && git commit -m "TICKET-XXX fix: description of hotfix"
git push origin hotfix-v4.7.1

# 3. Merge PR, then build and publish
hatch build && hatch publish
```

### Rolling Back a Merge

```bash
git revert -m 1 <merge-commit-hash>
git push origin main
```

---

## Contact

-   **Primary Maintainer**: Dipak Parmar (@dipakparmar)
-   **Team**: @ClaritiSoftware/cci-maintainers
-   **Email**: oss@claritisoftware.com
