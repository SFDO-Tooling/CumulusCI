# Maintainers Runbook

This document provides guidance for maintainers of Clariti CumulusCI.

## Table of Contents

- [Version Management](#version-management)
- [Python Version Requirements](#python-version-requirements)
- [Release Process](#release-process)
- [Syncing with Upstream](#syncing-with-upstream)
- [Key Files Reference](#key-files-reference)
- [Common Maintenance Tasks](#common-maintenance-tasks)

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

- **Release**: `4.6.0`
- **Development**: `4.6.0.dev1`
- **Beta**: `4.6.0b1`
- **Alpha**: `4.6.0a1`
- **Release Candidate**: `4.6.0rc1`

---

## Python Version Requirements

When changing the minimum Python version, update **ALL** of these locations:

### Files to Update

| File | Location | Current Value |
|------|----------|---------------|
| `pyproject.toml` | Line 10 | `requires-python = ">=3.11"` |
| `cumulusci/__init__.py` | Line 26 | `sys.version_info < (3, 11)` |
| `cumulusci/cli/utils.py` | Line 18 | `LOWEST_SUPPORTED_VERSION = (3, 11, 0)` |
| `cumulusci/cli/utils.py` | Line 108 | Error message mentioning Python version |
| `docs/get-started.md` | Line 72 | Python download instructions |
| `.github/workflows/*.yml` | Various | `python-version` in matrix |

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

### Creating a Release

```bash
# 1. Ensure you're on main and up to date
git checkout main
git pull origin main

# 2. Run tests
make test

# 3. Build docs
make docs

# 4. Create release branch
git checkout -b release-v4.7.0

# 5. Bump version
hatch version minor

# 6. Update changelog
# Edit docs/history.md

# 7. Commit and push
git add .
git commit -m "Release v4.7.0"
git push origin release-v4.7.0

# 8. Create PR and merge

# 9. Tag the release (after merge)
git checkout main
git pull origin main
git tag -a v4.7.0 -m "Release v4.7.0"
git push origin v4.7.0
```

### Publishing to PyPI

```bash
# Build the package
hatch build

# Check the build
twine check dist/*

# Upload to PyPI
twine upload dist/*
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

| File Category | Resolution |
|---------------|------------|
| Branding files (README, LICENSE, pyproject.toml) | Keep ours |
| Documentation URLs | Keep ours (claritisoftware.github.io) |
| Core functionality | Merge carefully, prefer upstream bug fixes |
| New features from upstream | Accept if compatible |
| CI/CD workflows | Review case by case |

---

## Key Files Reference

### Package Metadata

| File | Purpose |
|------|---------|
| `pyproject.toml` | Package configuration, dependencies, metadata |
| `cumulusci/__about__.py` | Version string (single source of truth) |
| `cumulusci/__init__.py` | Package initialization, version export |

### Branding & Legal

| File | Purpose |
|------|---------|
| `README.md` | Main project documentation |
| `LICENSE` | BSD 3-Clause license with copyrights |
| `LEGAL.md` | Legal compliance documentation |
| `AUTHORS.rst` | Contributors list |

### CLI & User-Facing

| File | Purpose |
|------|---------|
| `cumulusci/cli/utils.py` | Version checking, upgrade commands |
| `cumulusci/cli/error.py` | Error help URLs |
| `cumulusci/utils/__init__.py` | PIP/PIPX upgrade command strings |

### Documentation

| File | Purpose |
|------|---------|
| `docs/conf.py` | Sphinx configuration |
| `docs/get-started.md` | Installation instructions |
| `docs/contributing.md` | Contribution guidelines |

### CI/CD

| File | Purpose |
|------|---------|
| `.github/workflows/feature_test.yml` | Main CI workflow |
| `.github/workflows/docs.yml` | Documentation deployment |
| `.github/workflows/pre-release.yml` | Release automation |
| `.github/CODEOWNERS` | Code review assignments |

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
# 1. Yank from PyPI (doesn't delete, just hides)
pip install twine
twine upload --skip-existing dist/*  # This won't work for yanking

# Use PyPI web interface to yank the release

# 2. Create hotfix
git checkout -b hotfix-v4.7.1
# Fix the issue
hatch version patch
git commit -am "Hotfix: description"
git push origin hotfix-v4.7.1

# 3. Merge and release
```

### Rolling Back a Merge

```bash
git revert -m 1 <merge-commit-hash>
git push origin main
```

---

## Contact

- **Primary Maintainer**: Dipak Parmar (@dipakparmar)
- **Team**: @ClaritiSoftware/cci-maintainers
- **Email**: oss@claritisoftware.com
