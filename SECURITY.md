# Security Best Practices

This document outlines security best practices for this project to prevent accidental exposure of sensitive data.

## 🔐 Sensitive Data Guidelines

### What is Sensitive Data?

Sensitive data includes but is not limited to:
- API keys (Anthropic, OpenAI, Replicate, ElevenLabs, Gemini, etc.)
- AWS credentials (Access Key ID, Secret Access Key)
- Database connection strings with passwords
- Authentication tokens
- Private keys and certificates
- Session secrets
- OAuth client secrets
- Webhook signing secrets

### ✅ DO's

1. **Use Environment Variables**
   - Store all sensitive data in `.env` files (which are gitignored)
   - Use `.env.example` files to document required variables without actual values
   - Never commit `.env` files to version control

2. **Use Secrets Management**
   - Use GitHub Secrets for CI/CD workflows
   - Use AWS Secrets Manager for production deployments (see `terraform/secrets.tf`)
   - Use Terraform variables with `sensitive = true` flag

3. **Redact Sensitive Data in Documentation**
   - When documenting API responses or logs that contain sensitive data, replace actual values with placeholders like:
     - `REDACTED`
     - `<your-api-key>`
     - `xxxxxxxxxx`
   - Example:
     ```
     ❌ BAD:  "api_key": "sk-proj-abc123..."
     ✅ GOOD: "api_key": "REDACTED"
     ```

4. **Rotate Compromised Credentials**
   - If you accidentally commit sensitive data, immediately:
     1. Rotate/revoke the exposed credentials
     2. Remove them from the repository (including git history if needed)
     3. Notify team members
     4. Update any systems using the old credentials

### ❌ DON'Ts

1. **Never Hardcode Secrets**
   - Don't put API keys, passwords, or tokens directly in code
   - Don't commit configuration files with real credentials
   - Don't put credentials in comments

2. **Never Commit Sensitive Files**
   - Ensure `.env` files are in `.gitignore`
   - Don't commit `terraform.tfvars` with real values (use `terraform.tfvars.example`)
   - Don't commit private keys (`.pem`, `.key` files)

3. **Don't Share Presigned URLs**
   - AWS S3 presigned URLs contain temporary credentials
   - When documenting, redact the `AWSAccessKeyId` and `Signature` parameters
   - Example:
     ```
     ❌ BAD:  https://bucket.s3.amazonaws.com/file?AWSAccessKeyId=AKIA...&Signature=abc...
     ✅ GOOD: https://bucket.s3.amazonaws.com/file?AWSAccessKeyId=REDACTED&Signature=REDACTED
     ```

## 🛡️ Security Scanning

### Pre-commit Checks

Before committing code, run these checks:

```bash
# Check for accidentally staged .env files
git status | grep -E "\.env$"

# Search for potential API keys in staged files
git diff --cached | grep -iE "api[_-]?key|secret|token|password"

# Search for AWS credentials
git diff --cached | grep -E "AKIA[0-9A-Z]{16}"
```

### Automated Security Tools

This project uses:
- **GitHub Secret Scanning** - Automatically detects secrets pushed to the repository
- **CodeQL** - Static analysis for security vulnerabilities
- **Dependabot** - Security updates for dependencies

### Manual Security Audit

Periodically run manual security audits:

```bash
# Search for potential secrets in the codebase
git grep -iE "(api[_-]?key|token|password|secret).*=.*['\"][^'\"]{10,}['\"]"

# Check for AWS access keys
git grep -E "AKIA[0-9A-Z]{16}"

# Check for OpenAI API keys
git grep -E "sk-[A-Za-z0-9]{48}"

# Check for Replicate tokens
git grep -E "r8_[A-Za-z0-9]{40,}"
```

## 📝 Configuration Files

### Environment Variables

**Backend** (`.env` in `backend/` directory):
- See `backend/.env.example` for required variables
- All API keys should be set here
- Never commit this file

**Frontend** (`.env` in `frontend/` directory):
- See `frontend/.env.example` for required variables
- Use `NEXT_PUBLIC_` prefix for client-side variables
- Never commit this file

### Terraform

**Sensitive variables** (should be in `terraform/terraform.tfvars` - gitignored):
```hcl
# terraform/terraform.tfvars (DO NOT COMMIT)
anthropic_api_key = "your-actual-key"
openai_api_key = "your-actual-key"
# ... etc
```

**Variable declarations** (in `terraform/variables.tf` - committed):
```hcl
# Safe to commit - no actual values
variable "anthropic_api_key" {
  description = "Anthropic API Key (sensitive)"
  type        = string
  sensitive   = true
  default     = ""  # Empty default is safe
}
```

## 🚨 Incident Response

If sensitive data is accidentally committed:

1. **Immediately revoke/rotate the credentials**
   - AWS: Deactivate access keys in IAM console
   - API providers: Generate new keys and revoke old ones

2. **Remove from repository**
   ```bash
   # For recent commits not yet pushed
   git reset HEAD~1
   
   # For commits already pushed (requires force push - coordinate with team)
   # Consider using BFG Repo-Cleaner or git-filter-branch
   ```

3. **Notify the team**
   - Alert team members about the incident
   - Document what was exposed and when it was revoked

4. **Update dependent systems**
   - Update GitHub Secrets
   - Update AWS Secrets Manager
   - Update any local `.env` files

## 📚 Additional Resources

- [GitHub Secret Scanning](https://docs.github.com/en/code-security/secret-scanning)
- [AWS Security Best Practices](https://aws.amazon.com/security/best-practices/)
- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)

## 🔍 Recent Security Fixes

- **2024-11-24**: Removed exposed AWS Access Key ID from `.devdocs/v2/feats.md`
  - Redacted presigned S3 URL credentials in documentation
  - Added this security guidelines document

---

**Remember**: When in doubt, ask before committing anything that might contain sensitive data!
