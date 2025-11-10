#!/usr/bin/env python3
"""Generate markdown report for data gaps."""

import argparse
import json
from pathlib import Path


def generate_markdown_report(json_path: Path, output_path: Path) -> None:
    """Generate markdown report from JSON data."""
    with open(json_path) as f:
        data = json.load(f)

    metadata = data.get("metadata", {})
    summary = data.get("summary", {})
    priority_list = data.get("priority_list", [])

    report = f"""# Data Gaps Report

Generated: {metadata.get('generated_at', 'N/A')}

## Summary

- **Target Images per Zone**: {metadata.get('target_images_per_zone', 672)} (2 weeks = 672 images)
- **Collection Rate**: {metadata.get('collection_rate_images_per_day', 0):.1f} images/day
- **Total Zones**: {metadata.get('total_zones', 0)}
- **Zones with Sufficient Data**: {metadata.get('zones_sufficient', 0)}
- **Zones Needing More Images**: {metadata.get('zones_needing_more', 0)}

### Collection Statistics

- **Total Images Collected**: {summary.get('total_images_collected', 0)}
- **Total Images Needed**: {summary.get('total_images_needed', 0)}
- **Overall Completion**: {summary.get('overall_completion_percentage', 0):.1f}%

## Priority List (Top 20 Zones)

Zones needing the most images for full baseline:

| Zone | Current Images | Images Needed | Completion % | Est. Days |
|------|----------------|---------------|-------------|-----------|
"""

    for zone in priority_list:
        current = zone.get("current_images", 0)
        needed = zone.get("images_needed", 0)
        completion = zone.get("completion_percentage", 0)
        days = zone.get("estimated_days_to_complete", 0)
        days_str = f"{days:.1f}" if days else "N/A"
        report += f"| {zone['zone_number']} | {current} | {needed} | {completion:.1f}% | {days_str} |\n"

    report += f"""

## Estimated Timeline

Based on current collection rate of {metadata.get('collection_rate_images_per_day', 0):.1f} images/day:

- **Estimated Time to Full Baseline**: ~{priority_list[0].get('estimated_days_to_complete', 0):.1f} days (if zone with most images needed)
- **Estimated Completion Date**: {priority_list[0].get('estimated_completion_date', 'N/A')[:10] if priority_list else 'N/A'}

## Recommendations

1. **Focus Collection**: Prioritize zones with 0-1 images
2. **Monitor Progress**: Track collection rate and adjust as needed
3. **Partial Baselines**: Generate preliminary baselines with available data (≥3 images)
4. **Continuous Collection**: Maintain collection schedule to reach full baseline

## Data Collection Priority

### High Priority (0 images)
- Zone 9

### Medium Priority (1 image)
- Zones with only 1 image need 671 more images

### Lower Priority (2 images)
- Zones with 2 images need 670 more images

## Notes

- Full baseline requires 2 weeks of continuous collection
- Current collection rate: {metadata.get('collection_rate_images_per_day', 0):.1f} images/day
- All zones need more images to reach full baseline
- Partial baselines can be generated with ≥3 images per zone
"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(report)

    print(f"Markdown report saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate markdown report for data gaps")
    parser.add_argument(
        "--json-input",
        type=Path,
        default=Path("docs/reports/data_gaps.json"),
        help="Input JSON file (default: docs/reports/data_gaps.json)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/reports/data_gaps.md"),
        help="Output markdown file (default: docs/reports/data_gaps.md)",
    )

    args = parser.parse_args()

    if not args.json_input.exists():
        print(f"ERROR: JSON file not found: {args.json_input}")
        return 1

    generate_markdown_report(args.json_input, args.output)
    return 0


if __name__ == "__main__":
    exit(main())

