#!/usr/bin/env bash
# Push Pax repository to GitHub

set -e

cd "$(dirname "$0")"

echo "Pax NYC - Push to GitHub"
echo "========================"
echo ""

# Check if git is initialized
if [ ! -d .git ]; then
    echo "Git repository not initialized. Run ./setup_github.sh first"
    exit 1
fi

# Check remote
if ! git remote | grep -q origin; then
    echo "No GitHub remote configured. Run ./setup_github.sh first"
    exit 1
fi

REMOTE_URL=$(git remote get-url origin)
echo "Remote: $REMOTE_URL"
echo ""

# Safety check for API keys
echo "Checking for API keys..."
if git status --short | grep -E "\.env|key.*json|password"; then
    echo "WARNING: Credential files detected! Aborting."
    echo "Make sure .gitignore is up to date"
    exit 1
fi

# Add all files
echo "Staging files..."
git add .

# Check status
STATUS=$(git status --porcelain)
if [ -z "$STATUS" ]; then
    echo "No changes to commit"
else
    echo ""
    echo "Files to commit:"
    git status --short
    echo ""
    read -p "Commit message [Update Pax NYC collection system]: " COMMIT_MSG
    COMMIT_MSG=${COMMIT_MSG:-Update Pax NYC collection system}
    
    echo ""
    echo "Committing..."
    git commit -m "$COMMIT_MSG"
fi

# Check if main branch exists
if git rev-parse --verify main >/dev/null 2>&1; then
    BRANCH=main
elif git rev-parse --verify master >/dev/null 2>&1; then
    BRANCH=master
else
    BRANCH=main
    git branch -M main
fi

echo ""
echo "Pushing to GitHub ($BRANCH branch)..."
git push -u origin $BRANCH

echo ""
echo "Done! Repository pushed to: $REMOTE_URL"

