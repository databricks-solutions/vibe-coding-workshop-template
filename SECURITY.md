# Security Policy

## Reporting a Vulnerability

Please email bugbounty@databricks.com to report any security vulnerabilities. We will acknowledge receipt of your vulnerability and strive to send you regular updates about our progress. If you're curious about the status of your disclosure please feel free to email us again.

## Security Best Practices

When using this workshop template:

- **Never commit credentials**: Do not commit Databricks tokens, API keys, or other sensitive data to the repository
- **Use environment variables**: Store sensitive configuration in environment variables or `.env` files (which are gitignored)
- **Review code before execution**: Always review generated code before running it in production environments
- **Use least privilege**: Configure Databricks access with minimal required permissions
