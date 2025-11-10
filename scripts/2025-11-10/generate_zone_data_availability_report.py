#!/usr/bin/env python3
"""Generate markdown report for zone data availability."""

import argparse
import json
from pathlib import Path


def generate_markdown_report(json_path: Path, output_path: Path) -> None:
    """Generate markdown report from JSON data."""
    with open(json_path) as f:
        data = json.load(f)

    metadata = data.get("metadata", {})
    zones_sufficient = data.get("zones_sufficient", [])
    zones_partial = data.get("zones_partial", [])
    zones_missing = data.get("zones_missing", [])

    report = f"""# Zone Data Availability Report

Generated: {metadata.get('generated_at', 'N/A')}

## Summary

- **Total Zones**: {metadata.get('total_zones', 0)}
- **Zones with Sufficient Data (≥3 images)**: {metadata.get('zones_with_sufficient_data', 0)}
- **Zones with Partial Data (1-2 images)**: {metadata.get('zones_with_partial_data', 0)}
- **Zones with Missing Data (0 images)**: {metadata.get('zones_with_missing_data', 0)}
- **Total Images**: {metadata.get('total_images', 0)}

## Zones with Sufficient Data (≥3 images)

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

## Zones with Partial Data (1-2 images)

These zones have some data but need more images:

"""

    if zones_partial:
        report += "| Zone | Images | Cameras |\n"
        report += "|------|--------|----------|\n"
        for zone in zones_partial[:20]:  # Show first 20
            camera_count = len(zone.get("cameras", []))
            report += f"| {zone['zone_number']} | {zone['total_images']} | {camera_count} |\n"
        if len(zones_partial) > 20:
            report += f"\n*... and {len(zones_partial) - 20} more zones*\n"
    else:
        report += "*No zones with partial data.*\n"

    report += f"""

## Zones with Missing Data (0 images)

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

## Notes

- Sufficient data threshold: ≥3 images per zone
- Partial data: 1-2 images per zone
- Missing data: 0 images per zone
- Full baseline requires 2 weeks of collection (672 images per camera)
"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(report)

    print(f"Markdown report saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate markdown report for zone data availability")
    parser.add_argument(
        "--json-input",
        type=Path,
        default=Path("docs/reports/zone_data_availability.json"),
        help="Input JSON file (default: docs/reports/zone_data_availability.json)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/reports/zone_data_availability.md"),
        help="Output markdown file (default: docs/reports/zone_data_availability.md)",
    )

    args = parser.parse_args()

    if not args.json_input.exists():
        print(f"ERROR: JSON file not found: {args.json_input}")
        return 1

    generate_markdown_report(args.json_input, args.output)
    return 0


if __name__ == "__main__":
    exit(main())

