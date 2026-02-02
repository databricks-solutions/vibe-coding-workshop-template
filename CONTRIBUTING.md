# Contributing to Vibe Coding Workshop Template

This repository is maintained by Databricks Field Engineering and intended for contributions from Databricks Field Engineers. While the repository is public and meant to help anyone developing projects that use Databricks, external contributions are not currently accepted. Feel free to open an issue with requests or suggestions.

## Contact

For questions about this repository or to request access:
- Open an issue on this repository
- Contact the Databricks Field Engineering team

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/databricks-field-eng/vibe-coding-workshop-template.git
   cd vibe-coding-workshop-template
   ```

2. Set up the environment:
   ```bash
   ./scripts/setup.sh
   ```

3. Configure authentication:
   ```bash
   export DATABRICKS_HOST="https://your-workspace.cloud.databricks.com"
   export DATABRICKS_TOKEN="your-token"
   ```
   or use a profile from `~/.databrickscfg`:
   ```bash
   export DATABRICKS_CONFIG_PROFILE="your-profile"
   ```

## Code Standards

- **Python**: Follow PEP 8 conventions
- **Shell Scripts**: Use shellcheck for linting
- **Documentation**: Update relevant documentation when adding or modifying functionality
- **Type hints**: Include type annotations for public functions
- **Cursor Rules**: Follow the patterns defined in `.cursor/rules/`

## Pull Request Process

1. Create a feature branch from `main`
2. Make your changes with clear, descriptive commits
3. Test your changes against a Databricks workspace
4. Open a PR with:
   - Brief description of the change
   - Any relevant context or motivation
   - Testing performed
5. **Peer Review Required**: All published content must be peer-reviewed by at least one other team member and/or by an SME of the relevant subject
6. Address review feedback

## Adding New Prompts

When adding a new prompt to `context/prompts/`:

1. Follow the naming convention: `XX-descriptive-name-prompt.md`
2. Include clear instructions and examples
3. Reference relevant Cursor rules if applicable
4. Update the prompts README.md

## Adding New Cursor Rules

When adding a new rule to `.cursor/rules/`:

1. Place in the appropriate subdirectory (common, bronze, silver, gold, etc.)
2. Follow the naming convention: `XX-descriptive-name.mdc`
3. Include the standard frontmatter with description and globs
4. Update the table of contents in `00_TABLE_OF_CONTENTS.md`

## Security

- Never commit credentials, tokens, or sensitive data
- Use synthetic data for examples and tests
- Review changes for potential security issues before submitting
- See [SECURITY.md](SECURITY.md) for vulnerability reporting

## License

By submitting a contribution, you agree that your contributions will be licensed under the same terms as the project (see [LICENSE.md](LICENSE.md)).

You certify that:
- You have the right to submit the contribution
- Your contribution does not include confidential or proprietary information
- You grant Databricks the right to use, modify, and distribute your contribution
