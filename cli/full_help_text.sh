OUTPUT=help.md

echo "# Full help text for the cumulusci command" > "$OUTPUT"
echo "" >> "$OUTPUT"
echo "## cumulusci" >> "$OUTPUT"
echo "" >> "$OUTPUT"
echo "cumulusci" >> "$OUTPUT"
echo "" >> "$OUTPUT"
cumulusci | sed -e 's/^/    /g' >> "$OUTPUT"
echo "" >> "$OUTPUT"


echo "## (dev) For Developers" >> "$OUTPUT"
echo "" >> "$OUTPUT"

echo "cumulusci dev" >> "$OUTPUT"
echo "" >> "$OUTPUT"
cumulusci dev | sed -e 's/^/    /g' >> "$OUTPUT"
echo "" >> "$OUTPUT"

echo "cumulusci dev apextestsdb_upload --help" >> "$OUTPUT"
echo "" >> "$OUTPUT"
cumulusci dev apextestsdb_upload --help | sed -e 's/^/    /g' >> "$OUTPUT"
echo "" >> "$OUTPUT"

echo "cumulusci dev deploy --help" >> "$OUTPUT"
echo "" >> "$OUTPUT"
cumulusci dev deploy --help | sed -e 's/^/    /g' >> "$OUTPUT"
echo "" >> "$OUTPUT"

echo "cumulusci dev deploy_managed --help" >> "$OUTPUT"
echo "" >> "$OUTPUT"
cumulusci dev deploy_managed --help | sed -e 's/^/    /g' >> "$OUTPUT"
echo "" >> "$OUTPUT"

echo "cumulusci dev run_tests --help" >> "$OUTPUT"
echo "" >> "$OUTPUT"
cumulusci dev run_tests --help | sed -e 's/^/    /g' >> "$OUTPUT"
echo "" >> "$OUTPUT"

echo "cumulusci dev update_package_xml --help" >> "$OUTPUT"
echo "" >> "$OUTPUT"
cumulusci dev update_package_xml --help | sed -e 's/^/    /g' >> "$OUTPUT"
echo "" >> "$OUTPUT"


echo "## (release) For Release Managers" >> "$OUTPUT"
echo "" >> "$OUTPUT"

echo "cumulusci release" >> "$OUTPUT"
echo "" >> "$OUTPUT"
cumulusci release | sed -e 's/^/    /g' >> "$OUTPUT"
echo "" >> "$OUTPUT"

echo "cumulusci release deploy --help" >> "$OUTPUT"
echo "" >> "$OUTPUT"
cumulusci release deploy --help | sed -e 's/^/    /g' >> "$OUTPUT"
echo "" >> "$OUTPUT"

echo "cumulusci release upload_beta --help" >> "$OUTPUT"
echo "" >> "$OUTPUT"
cumulusci release upload_beta --help | sed -e 's/^/    /g' >> "$OUTPUT"
echo "" >> "$OUTPUT"


echo "## (github) Github Scripts" >> "$OUTPUT"
echo "" >> "$OUTPUT"

echo "cumulusci github" >> "$OUTPUT"
echo "" >> "$OUTPUT"
cumulusci github | sed -e 's/^/    /g' >> "$OUTPUT"
echo "" >> "$OUTPUT"

echo "cumulusci github release --help" >> "$OUTPUT"
echo "" >> "$OUTPUT"
cumulusci github release --help | sed -e 's/^/    /g' >> "$OUTPUT"
echo "" >> "$OUTPUT"

echo "cumulusci github release_notes --help" >> "$OUTPUT"
echo "" >> "$OUTPUT"
cumulusci github release_notes --help | sed -e 's/^/    /g' >> "$OUTPUT"
echo "" >> "$OUTPUT"

echo "cumulusci github commit_status --help" >> "$OUTPUT"
echo "" >> "$OUTPUT"
cumulusci github commit_status --help | sed -e 's/^/    /g' >> "$OUTPUT"
echo "" >> "$OUTPUT"

echo "cumulusci github clone_tag --help" >> "$OUTPUT"
cumulusci github clone_tag --help | sed -e 's/^/    /g' >> "$OUTPUT"
echo "" >> "$OUTPUT"
echo "cumulusci github master_to_feature --help" >> "$OUTPUT"

echo "" >> "$OUTPUT"
cumulusci github master_to_feature --help | sed -e 's/^/    /g' >> "$OUTPUT"
echo "" >> "$OUTPUT"


echo "## (ci) Continuous Integration" >> "$OUTPUT"
echo "" >> "$OUTPUT"

echo "cumulusci ci" >> "$OUTPUT"
echo "" >> "$OUTPUT"
cumulusci ci | sed -e 's/^/    /g' >> "$OUTPUT"
echo "" >> "$OUTPUT"

echo "cumulusci ci deploy --help" >> "$OUTPUT"
echo "" >> "$OUTPUT"
cumulusci ci deploy --help | sed -e 's/^/    /g' >> "$OUTPUT"
echo "" >> "$OUTPUT"

echo "cumulusci ci beta_deploy --help" >> "$OUTPUT"
echo "" >> "$OUTPUT"
cumulusci ci beta_deploy --help | sed -e 's/^/    /g' >> "$OUTPUT"
echo "" >> "$OUTPUT"

echo "cumulusci ci apextestsdb --help" >> "$OUTPUT"
echo "" >> "$OUTPUT"
cumulusci ci apextestsdb --help | sed -e 's/^/    /g' >> "$OUTPUT"
echo "" >> "$OUTPUT"

echo "cumulusci ci next_step --help" >> "$OUTPUT"
echo "" >> "$OUTPUT"
cumulusci ci next_step --help | sed -e 's/^/    /g' >> "$OUTPUT"
echo "" >> "$OUTPUT"

grep -v 'Detected .* build of branch' help.md > help_clean.md
