# Halloy Theme Phase 06 — Configuration and Persistence Migration

> **Plan status: HISTORICAL — shipped.** The outcome is documented in [architecture/core/themes.md](../architecture/core/themes.md); this file is the historical record.

## Objective

Replace the legacy single preset setting with durable Halloy theme configuration while preserving existing installations and keeping runtime rendering behavior unchanged until Phase 07.

## Scope

This phase owns:

- application configuration for bundled/external themes;
- database schema and migration work;
- legacy preset compatibility;
- startup validation and fallback policy;
- environment/config precedence;
- tests for upgrade and invalid configuration paths.

It does not yet replace `THEME_PRESETS` in templates.

## Target data model

Preferred `SiteSettings` fields:

```text
theme_dark_name      String(128), non-null, default known-good dark theme
theme_light_name     String(128), non-null, default known-good light theme
theme_default_scheme String(16),  non-null, one of system/dark/light
```

Retain `syntax_theme`, `custom_css_enabled`, and `custom_css` unchanged.

The existing `theme_preset` field may be retained temporarily as a compatibility column or migrated into the new fields and deprecated. Avoid destructive removal in the same migration unless downgrade and rollback behavior are well defined.

## Application configuration

Add a cohesive theme configuration section, for example:

```toml
[themes]
external_dir = ""
allow_external = true
strict_validation = false
default_dark = "Catppuccin Mocha"
default_light = "Catppuccin Latte"
default_scheme = "system"
```

Configuration responsibilities:

- external directory location;
- whether external themes are enabled;
- built-in fallback names;
- optional strict validation;
- operator defaults used when database settings are absent or invalid.

Environment overrides should follow existing project conventions. Do not introduce a second independent configuration loader.

## Migration strategy

Map legacy values deterministically:

- `github-dark` → selected bundled dark equivalent;
- `github-light` → selected bundled light equivalent;
- `solarized-dark` → `Solarized Dark`;
- `monokai` → closest documented bundled equivalent;
- unknown value → configured defaults with warning.

Migration requirements:

- existing rows upgrade without manual intervention;
- long names and spaces are supported;
- downgrade behavior is documented;
- no migration imports Flask request state;
- migration remains safe on supported SQLite and PostgreSQL deployments.

## Validation service

Add a server-side helper that validates persisted names against `ThemeRegistry` and returns effective values plus warnings.

Validation should distinguish:

- invalid syntax;
- missing theme;
- malformed selected external theme;
- disabled external theme source;
- fallback activation.

Invalid settings must not prevent public startup by default. Strict mode may fail startup only when explicitly configured.

## Precedence

Define and document:

1. persisted site setting;
2. application theme default;
3. registry default;
4. emergency theme.

External-directory configuration is application-level, not persisted per visitor.

## Admin form preparation

Update backend form models/validators as needed so later admin UI work can submit named dark/light themes and a default scheme. Do not build dynamic selectors or preview in this phase.

Reject arbitrary paths and values not represented by registry names.

## Tests

Cover:

- fresh database defaults;
- migration from every legacy preset;
- unknown legacy value;
- names longer than 32 characters;
- names containing spaces and parentheses;
- valid bundled and external selections;
- missing external directory;
- malformed selected theme;
- external themes disabled;
- strict versus non-strict validation;
- SQLite and migration metadata consistency;
- syntax theme and custom CSS preservation.

## Expected files

Likely changes:

- `app/models.py`;
- configuration models/loaders;
- admin form validation modules;
- Alembic migration(s);
- `config.toml.example` and environment documentation;
- theme settings service module;
- migration and configuration tests.

## Acceptance criteria

- New installations receive valid dark/light Halloy defaults.
- Existing preset selections migrate predictably.
- Theme names are stored without truncation.
- Invalid persisted values fall back safely with actionable logs.
- External theme enablement and directory configuration are explicit.
- Syntax themes and custom CSS remain unaffected.
- Runtime templates still use the legacy renderer until Phase 07, preventing a half-integrated state.
