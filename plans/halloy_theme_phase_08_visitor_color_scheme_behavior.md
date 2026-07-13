# Halloy Theme Phase 08 — Visitor Color-Scheme Behavior

## Objective

Replace the current ambiguous dark-mode toggle with a color-scheme preference model that works cleanly with administrator-selected Halloy dark/light theme pairs and avoids first-paint flashing.

## Target model

Separate theme identity from visitor preference:

- administrator selects one dark Halloy theme and one light Halloy theme;
- visitor preference is one of `system`, `dark`, or `light`;
- browser storage never contains an unrestricted filesystem path or raw TOML filename outside registry names;
- server-rendered CSS contains both translated palettes.

## Storage contract

Replace the generic `localStorage.theme` key with a namespaced key such as:

```text
blog-color-scheme
```

Accepted values:

```text
system
dark
light
```

Migration behavior:

- existing `theme=dark` maps to `dark`;
- existing `theme=light` maps to `light`;
- absent or unknown values map to `system`;
- old keys may be removed after successful migration.

## First-paint bootstrap

Add a minimal nonce-bearing inline bootstrap in `<head>` before deferred CSS/JS can paint the wrong scheme.

The bootstrap should:

1. read the stored preference defensively;
2. resolve `system` through `matchMedia('(prefers-color-scheme: dark)')`;
3. set `data-color-scheme` on `<html>`;
4. set `color-scheme` metadata/property where appropriate;
5. avoid throwing when storage is unavailable;
6. contain no network or dynamic code loading.

Do not wait for `DOMContentLoaded`.

## Runtime controller

Refactor `app/static/js/shared/dark-mode.js` or replace it with a focused color-scheme controller.

Responsibilities:

- expose current explicit preference and effective scheme;
- update the root attribute;
- persist explicit choices;
- listen for system preference changes only when preference is `system`;
- update accessible labels, title, and pressed/state attributes;
- avoid duplicate listeners during partial navigation or repeated initialization.

## Control UX

Prefer a three-state control where design permits:

- System;
- Dark;
- Light.

A compact cycling button is acceptable if its current state and next action are unambiguous to assistive technology. A select/radio group in settings plus a quick toggle may be clearer.

Requirements:

- keyboard operable;
- visible focus state;
- descriptive `aria-label`;
- no color-only state communication;
- touch target meets existing accessibility conventions.

## CSS migration

Replace palette ownership under `[data-theme="light"]` with Halloy-generated selectors under `[data-color-scheme]`.

Remove or neutralize static variable blocks that would override generated Halloy palettes. Structural rules that differ by scheme should use semantic tokens whenever possible.

Set browser-native form/control scheme appropriately so inputs, scrollbars, and built-in widgets remain legible.

## Server interaction

The first release may keep visitor preference client-only. The server should emit the configured default scheme for no-JS rendering and both theme variable sets.

Do not add cookies or account-level preference persistence unless explicitly required. If cookies are later added, define CSP/cache implications separately.

## Tests

Add unit/browser tests for:

- absent storage → system behavior;
- migrated legacy dark/light value;
- explicit dark and light persistence;
- system preference change updates effective scheme;
- explicit preference ignores subsequent system changes;
- invalid storage value recovery;
- storage access exception handling;
- root attribute applied before application initialization;
- accessible label/state updates;
- JavaScript-disabled rendering uses the configured default scheme;
- no stale `data-theme` palette authority remains.

Use browser automation for first-paint behavior where practical. A DOM unit test alone cannot fully prove absence of FOUC.

## Expected files

Likely:

- `app/templates/base.html` and login/admin bases;
- `app/static/js/shared/dark-mode.js` or replacement;
- base/critical CSS;
- navigation/theme control templates;
- JavaScript and browser tests;
- accessibility and configuration documentation.

## Acceptance criteria

- Theme identity and visitor scheme preference are separate concepts.
- `system`, `dark`, and `light` are the only supported preference values.
- The correct scheme attribute is set before first paint.
- System changes are observed only in system mode.
- Existing dark/light preferences migrate without surprising resets.
- Static light-theme variables no longer override Halloy output.
- The control is keyboard and screen-reader accessible.
