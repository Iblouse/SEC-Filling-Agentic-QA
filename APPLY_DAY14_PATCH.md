# Apply the Day 14 Patch

From the repository root:

```bash
rm -rf /tmp/day-14-cicd-security-hardening-patch
unzip ~/Downloads/day-14-cicd-security-hardening-patch.zip -d /tmp
cp -R /tmp/day-14-cicd-security-hardening-patch/. .
chmod +x \
  scripts/configure_day14_api_key.sh \
  scripts/configure_github_day14.sh \
  scripts/smoke_test_day14.sh \
  scripts/verify_day14_security.sh
```

Review before running Terraform:

```bash
git status --short
git diff --stat
make check
terraform -chdir=infrastructure/portfolio fmt
terraform -chdir=infrastructure/portfolio validate
```
