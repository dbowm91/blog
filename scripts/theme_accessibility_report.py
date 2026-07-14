#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.themes.diagnostics import (
    CatalogAccessibilityReport,
    validate_catalog_accessibility,
    validate_theme_accessibility,
)
from app.themes.halloy import parse_halloy_theme
from app.themes.model import BlogTheme
from app.themes.translate import translate_halloy_theme

CATALOG_DIR = Path(__file__).resolve().parent.parent / "themes"


def _load_theme_report(path: Path) -> tuple[BlogTheme, bool, str]:
    theme = parse_halloy_theme(path)
    result = translate_halloy_theme(theme)
    return result.theme, result.is_dark, path.stem


def generate_report(
    catalog_dir: Path = CATALOG_DIR,
    source_filter: str = "all",
) -> CatalogAccessibilityReport:
    toml_files = sorted(p for p in catalog_dir.glob("*.toml") if not p.name.startswith("._"))
    reports = []
    for path in toml_files:
        blog_theme, is_dark, name = _load_theme_report(path)
        report = validate_theme_accessibility(
            blog_theme,
            theme_name=name,
            filename_dark=is_dark,
        )
        report = report.__class__(
            theme_name=report.theme_name,
            source="bundled",
            is_dark=report.is_dark,
            findings=report.findings,
            classification=report.classification,
        )
        reports.append(report)
    return validate_catalog_accessibility(reports)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate theme accessibility quality report")
    parser.add_argument("--json", "as_json", action="store_true", help="Output as JSON")
    parser.add_argument("--catalog-dir", type=Path, default=CATALOG_DIR, help="Catalog directory")
    parser.add_argument(
        "--source",
        choices=["all", "bundled", "external"],
        default="all",
        help="Filter by source",
    )
    args = parser.parse_args()

    report = generate_report(args.catalog_dir, args.source)

    if args.as_json:
        print(json.dumps(report.to_dict(), indent=2))
        return

    print("Theme Accessibility Quality Report")
    print(f"{'=' * 50}")
    print(f"Total themes:      {report.total_themes}")
    print(f"Passed:            {report.passed_count}")
    print(f"Failed:            {report.failed_count}")
    print(f"Mandatory failures: {report.total_mandatory}")
    print(f"Advisory warnings:  {report.total_advisory}")
    mismatches = report.classification_mismatches
    if mismatches:
        print(f"Classification mismatches: {len(mismatches)}")
        for m in mismatches:
            print(
                f"  - {m.theme_name}: filename_dark={m.filename_dark} computed_dark={m.computed_dark}"
            )

    if report.failed_count > 0:
        print("\nFailed themes:")
        for r in report.reports:
            if not r.passed:
                print(f"\n  {r.theme_name}:")
                for f in r.mandatory_failures:
                    print(f"    [FAIL] {f.description} ({f.ratio}:1, required {f.required}:1)")
                    print(f"           fg={f.foreground} bg={f.background}")

    worst = report.worst_findings
    if worst:
        print("\nWorst contrast pairs:")
        for f in worst[:5]:
            print(f"  {f.theme_name}: {f.description} ({f.ratio}:1, WCAG {f.wcag})")

    print(f"\n{'=' * 50}")
    if report.failed_count == 0:
        print("All themes pass mandatory accessibility gates!")
    else:
        print(f"{report.failed_count} theme(s) have mandatory failures.")
        sys.exit(1)


if __name__ == "__main__":
    main()
