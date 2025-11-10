# Pax Corridor Toolkit (Reset)

This repository is being rebuilt around a street-network-first workflow for the Midtown corridor (34th–66th St, Lexington Ave to 9th Ave). All prior longitude-driven scripts have been archived under `docs/backup_20251105_150716/`.

## Current status

- Project skeleton reinstated (`pyproject.toml`, `src/pax`)
- Upcoming work: street-network-based camera selection and Voronoi zone generation

## Data dependencies

- NYC Planning Digital City Map street centerlines (`docs/termprojectproposal_bkup/.../DCM_StreetCenterLine.*`)
- `nyc_cameras_full.json` snapshot under `docs/termprojectproposal_bkup`

## Next steps

1. Build corridor polygon from DCM street data (Lexington through 9th).
2. Filter cameras by street membership rather than latitude/longitude thresholds.
3. Regenerate Voronoi zones and visualization assets against the new manifest.
