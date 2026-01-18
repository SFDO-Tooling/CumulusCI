# Legal Compliance

## License Summary

Clariti CumulusCI is a fork of [CumulusCI](https://github.com/SFDO-Tooling/CumulusCI), which is licensed under the **BSD 3-Clause License**.

### What the BSD 3-Clause License Allows

- **Commercial use**: You can use, modify, and distribute this software commercially
- **Modification**: You can modify the source code
- **Distribution**: You can distribute the software
- **Private use**: You can use the software privately

### What the BSD 3-Clause License Requires

1. **Copyright notice retention**: All redistributions must include the original copyright notice
2. **License text inclusion**: The license text must be included in distributions
3. **No endorsement**: The names of the original authors (Salesforce.com) cannot be used to endorse or promote products derived from this software without prior written permission

### What We Have Done to Comply

| Requirement | Compliance |
|-------------|------------|
| Original copyright retained | Yes - `Copyright (c) 2021, Salesforce.com, Inc.` in LICENSE |
| Fork copyright added | Yes - `Copyright (c) 2025, Clariti Cloud Inc.` in LICENSE |
| License text preserved | Yes - Full BSD 3-Clause text in LICENSE |
| Original project attribution | Yes - Link to upstream in LICENSE, README, pyproject.toml |
| No false endorsement | Yes - We do not claim Salesforce endorsement |

## Trademark Considerations

- **"CumulusCI"** - We use this name descriptively to indicate compatibility with the original project
- **"Salesforce"** - We do not use Salesforce trademarks in our branding, only in factual attribution
- **"Clariti CumulusCI"** - Our package name clearly distinguishes this as a Clariti-maintained fork

## What We Can and Cannot Do

### We CAN:
- Publish to PyPI under a different package name (`clariti-cumulusci`)
- Modify the code and add new features
- Change branding, documentation, and URLs
- Use commercially within Clariti and by our customers
- Accept contributions under the same BSD license

### We CANNOT:
- Remove original copyright notices
- Claim Salesforce/SFDO endorsement
- Use "Salesforce" in our package name or branding
- Remove or change the BSD license for our fork

## Third-Party Dependencies

This project includes dependencies that have their own licenses. Key dependencies:

| Package | License | Notes |
|---------|---------|-------|
| simple-salesforce | Apache 2.0 | Compatible with BSD |
| click | BSD 3-Clause | Same license family |
| requests | Apache 2.0 | Compatible with BSD |
| pyyaml | MIT | Compatible with BSD |
| robotframework | Apache 2.0 | Compatible with BSD |
| snowfakery | BSD 3-Clause | Same license |

All dependencies are compatible with BSD 3-Clause licensing.

## Recommendations for Maintainers

1. **When adding new code**: New code written by Clariti falls under our copyright (2025, Clariti Cloud Inc.)
2. **When accepting contributions**: Contributors agree to license their code under BSD 3-Clause
3. **When syncing from upstream**: Preserve any new copyright notices from upstream
4. **When adding dependencies**: Verify license compatibility (BSD, MIT, Apache 2.0 are all compatible)

## Contact

For legal questions regarding this fork, contact: oss@claritisoftware.com

---

*This document is for informational purposes and does not constitute legal advice. Consult with legal counsel for specific legal questions.*
