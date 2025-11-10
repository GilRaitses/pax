#!/usr/bin/env python3
"""Generate markdown report for data completeness."""

import argparse
import json
from pathlib import Path


def generate_markdown_report(json_path: Path, output_path: Path) -> None:
    """Generate markdown report from JSON data."""
    with open(json_path) as f:
        data = json.load(f)

    metadata = data.get("metadata", {})
    summary = data.get("summary", {})
    zones_sufficient = data.get("zones_sufficient", [])
    zones_partial = data.get("zones_partial", [])
    zones_missing = data.get("zones_missing", [])

    report = f"""# Data Completeness Report

## Summary

- **Total Zones**: {metadata.get('total_zones', 0)}
- **Zones with Sufficient Data (≥3 images)**: {metadata.get('zones_sufficient', 0)} ({summary.get('sufficient_percentage', 0):.1f}%)
- **Zones with Partial Data (1-2 images)**: {metadata.get('zones_partial', 0)} ({summary.get('partial_percentage', 0):.1f}%)
- **Zones with Missing Data (0 images)**: {metadata.get('zones_missing', 0)} ({summary.get('missing_percentage', 0):.1f}%)
- **Total Images**: {metadata.get('total_images', 0)}
- **Sufficient Threshold**: {metadata.get('sufficient_threshold', 3)} images

## Zones by Data Completeness

### Zones with Sufficient Data (≥3 images)

These zones have enough images for baseline generation:

"""

    if zones_sufficient:
        report += "| Zone | Images | Cameras |\n"
        report += "|------|--------|----------|\n"
        for zone in zones_sufficient:
            camera_count = len(zone.get("cameras", []))
            report += f"| {zone['zone_number']} | {zone['total_images']} | {camera_count} |\n"
    else:
        report += "*No zones have sufficient data yet.*\n"

    report += f"""

### Zones with Partial Data (1-2 images)

These zones have some data but need more images:

"""

    if zones_partial:
        report += "| Zone | Images | Cameras |\n"
        report += "|------|--------|----------|\n"
        for zone in zones_partial[:30]:  # Show first 30
            camera_count = len(zone.get("cameras", []))
            report += f"| {zone['zone_number']} | {zone['total_images']} | {camera_count} |\n"
        if len(zones_partial) > 30:
            report += f"\n*... and {len(zones_partial) - 30} more zones*\n"
    else:
        report += "*No zones with partial data.*\n"

    report += f"""

### Zones with Missing Data (0 images)

These zones have no images collected yet:

"""

    if zones_missing:
        report += "| Zone | Cameras |\n"
        report += "|------|----------|\n"
        for zone in zones_missing:
            camera_count = len(zone.get("cameras", []))
            report += f"| {zone['zone_number']} | {camera_count} |\n"
    else:
        report += "*All zones have at least some data.*\n"

    report += """

## Recommendations

1. **Priority Zones**: Focus collection efforts on zones with missing or partial data
2. **Sufficient Data**: Zones with ≥3 images can be used for preliminary baseline generation
3. **Full Baseline**: Requires 2 weeks of continuous collection (672 images per camera)
4. **Collection Rate**: Monitor collection rate to estimate completion timeline

## Next Steps

- Continue data collection to reach ≥3 images per zone
- Extract features from available images
- Generate preliminary stress scores
- Update baseline as more data becomes available
"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(report)

    print(f"Markdown report saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate markdown report for data completeness")
    parser.add_argument(
        "--json-input",
        type=Path,
        default=Path("docs/reports/data_completeness.json"),
        help="Input JSON file (default: docs/reports/data_completeness.json)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/reports/data_completeness.md"),
        help="Output markdown file (default: docs/reports/data_completeness.md)",
    )

    args = parser.parse_args()

    if not args.json_input.exists():
        print(f"ERROR: JSON file not found: {args.json_input}")
        return 1

    generate_markdown_report(args.json_input, args.output)
    return 0


if __name__ == "__main__":
    exit(main())

