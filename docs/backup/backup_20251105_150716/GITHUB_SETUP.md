# GitHub Repository Setup

## Quick Setup

### Option 1: Use Setup Scripts

```bash
cd ~/pax

# First, create the repository on GitHub (or use setup script)
./setup_github.sh

# Then push everything
./push_to_github.sh
```

### Option 2: Manual Setup

1. **Create repository on GitHub:**
   - Go to https://github.com/new
   - Repository name: `pax` (or your choice)
   - Description: "Energetic pathfinding and perceptual heuristics in Manhattan navigation"
   - Make it public or private
   - Don't initialize with README (we already have one)

2. **Connect local repo to GitHub:**

```bash
cd ~/pax

# Set remote (replace USERNAME with your GitHub username)
git remote add origin https://github.com/USERNAME/pax.git

# Or if using SSH:
git remote add origin git@github.com:USERNAME/pax.git
```

3. **Make initial commit:**

```bash
git add .
git commit -m "Initial commit: Pax NYC camera collection system

- Camera manifest for Grand Central-Carnegie Hall corridor (40 cameras)
- Live dashboard for monitoring collection
- Data collection scripts with NYCTMC API integration
- Cloud Run deployment infrastructure
- Daily email notification system
- CIS 667 term project proposal"

git branch -M main
git push -u origin main
```

## What Gets Pushed

The repository includes:

- **Source code**: All Python scripts and configuration
- **Documentation**: README, setup guides, manifest docs
- **Project proposal**: CIS667_TermProject_Proposal_Final.pdf and .qmd
- **Infrastructure**: Cloud Run deployment scripts
- **Dashboard**: Live HTML dashboard
- **Camera manifest**: 40-camera corridor definition

**Excluded** (via `.gitignore`):
- `data/` directory (collected images/metadata)
- `.env` file (credentials)
- Service account keys
- Email credentials
- Virtual environment

## GitHub Actions (Optional)

You can add a GitHub Actions workflow for automated testing:

```yaml
# .github/workflows/test.yml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - run: pip install -e .
      - run: python -m pytest
```

## Troubleshooting

### "Repository not found"
- Double-check the repository name and your GitHub username
- Make sure you've created the repo on GitHub first
- Verify remote URL: `git remote -v`

### "Permission denied"
- Use SSH instead of HTTPS: `git remote set-url origin git@github.com:USERNAME/pax.git`
- Or use a Personal Access Token instead of password

### "Nothing to commit"
- Files might be ignored: check `.gitignore`
- Or already committed: `git log` to see commits

### Need to update remote URL

```bash
git remote remove origin
git remote add origin https://github.com/USERNAME/pax.git
```

## Repository Contents Summary

```
pax/
├── src/pax/                    # Python package
│   ├── scripts/               # CLI tools (collect, warehouse, stats_api, daily_export)
│   ├── data_collection/       # Camera API client
│   ├── storage/               # GCS uploader
│   └── warehouse/             # Parquet builder
├── docs/
│   └── index.html             # Live dashboard
├── infra/
│   ├── cloudrun/              # Cloud Run deployment
│   └── bootstrap_collection.sh
├── cameras.yaml               # 40-camera manifest
├── CIS667_TermProject_Proposal_Final.pdf
├── CIS667_TermProject_Proposal_Final.qmd
├── README.md
└── setup scripts (setup_github.sh, push_to_github.sh)
```

## After Pushing

1. **Add repository description** on GitHub:
   "Energetic pathfinding and perceptual heuristics for Manhattan pedestrian navigation. CIS 667 term project."

2. **Add topics** (on GitHub repo page):
   - `cis667`
   - `manhattan`
   - `traffic-cameras`
   - `pathfinding`
   - `heuristic-search`
   - `python`

3. **Update README** if needed with:
   - Project description
   - Quick start guide
   - Link to proposal PDF

4. **Enable GitHub Pages** (optional) to host dashboard:
   - Settings > Pages
   - Source: `docs` folder
   - Your dashboard will be at: `https://USERNAME.github.io/pax/`

