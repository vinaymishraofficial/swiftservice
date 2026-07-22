# Contributing to SwiftService

Thank you for your interest in contributing to SwiftService.

SwiftService is an open-source field service app for Frappe/ERPNext. Contributions
can be bug reports, feature requests, documentation updates, or code changes.

Please also follow our [Code of Conduct](./CODE_OF_CONDUCT.md).

## Ways to Contribute

- Report bugs
- Suggest features or improvements
- Improve documentation
- Submit pull requests for bug fixes or features
- Help review pull requests

## Before You Start

1. Search existing [issues](https://github.com/vinaymishraofficial/swiftservice/issues)
   and pull requests to avoid duplicates.
2. For larger changes, open an issue first to discuss the approach.
3. Keep one pull request focused on one change.

## Development Setup

From your Frappe bench root:

```bash
bench get-app https://github.com/vinaymishraofficial/swiftservice.git
bench --site <your-site> install-app swiftservice
```

Frontend:

```bash
cd apps/swiftservice/frontend
yarn install
yarn build
```

Then clear cache:

```bash
bench --site <your-site> clear-cache
```

Optional quality checks:

```bash
cd apps/swiftservice
pre-commit install
pre-commit run --all-files
```

## Branching

- Use `develop` for day-to-day contributions
- Use `Production` for stable production releases

Open pull requests against `develop` unless maintainers ask otherwise.

## Pull Request Guidelines

1. Keep changes focused and easy to review.
2. Include a clear description of the problem and solution.
3. Mention related issue numbers when applicable.
4. Add screenshots or recordings for UI changes.
5. Update docs/README if behavior or setup steps change.
6. Do not commit secrets, API keys, or generated build artifacts.

Suggested PR checklist:

- [ ] Works on a local bench site
- [ ] Frontend rebuilt if Vue files changed (`yarn build`)
- [ ] No unrelated formatting-only noise
- [ ] Docs updated where needed

## Bug Reports

Please include:

1. Steps to reproduce
2. Expected vs actual behavior
3. Frappe / ERPNext / SwiftService versions when possible
4. Screenshots, logs, or browser console errors
5. A clear, specific title

## Feature Requests

Please include:

1. The problem you are trying to solve
2. Proposed behavior
3. Why it helps field-service workflows
4. Mockups or examples if available

## Security Issues

Do not open a public issue for security vulnerabilities.
Follow [SECURITY.md](./SECURITY.md) instead.

## License

By contributing, you agree that your contributions will be licensed under the
same terms as this project: [GNU GPL v3](./LICENSE).
