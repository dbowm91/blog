# DevLog Documentation

Guides for using, installing, and operating DevLog. For implementation details, see the [architecture overview](../architecture/overview.md).

## Start here

| Guide | Use it for |
|---|---|
| [Project overview](../README.md) | Features and quick start |
| [User guide](../USAGE.md) | Writing and day-to-day administration |
| [Installation](installation.md) | Native, Docker, and local development setup |
| [Deployment](../DEPLOY.md) | Production deployment and operations |

## Operations and API

| Guide | Use it for |
|---|---|
| [Filesystem layout](filesystem-layout.md) | Where configuration, content, and runtime files are stored |
| [Migration from a checkout](migration-from-checkout.md) | Planning a move from a development checkout to a production layout |
| [API reference](api/posts.md) | Authentication, scopes, and endpoint details |
| [OpenAPI specification](openapi.yaml) | Machine-readable API schema, also served at `/api/docs` |

## Themes

| Guide | Use it for |
|---|---|
| [Theme operator guide](themes/operator-guide.md) | Selecting, validating, and installing themes |
| [Supported schema](themes/supported-schema.md) | Authoring a Halloy-compatible theme file |
| [Theme token contract](themes/blog-theme-contract.md) | Understanding the tokens DevLog generates |
| [Accessibility policy](themes/accessibility-policy.md) | Contrast requirements and theme classifications |

Advanced theme implementation notes are in [theme references](themes/).

## Development and security

- [Contributing](../CONTRIBUTING.md) describes the development workflow.
- [Security policy](../SECURITY.md) explains vulnerability reporting.
- [CLI reference](../architecture/deployment/cli.md) documents operator commands.
- [Release history](../CHANGELOG.md) records shipped changes.
