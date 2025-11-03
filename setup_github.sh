#!/usr/bin/env bash
# Setup GitHub repository for Pax

set -e

echo "Pax NYC - GitHub Repository Setup"
echo "=================================="
echo ""

# Check if git is initialized
if [ ! -d .git ]; then
    echo "Initializing git repository..."
    git init
    git branch -M main
fi

# Check current remote
if git remote | grep -q origin; then
    CURRENT_REMOTE=$(git remote get-url origin)
    echo "Current remote: $CURRENT_REMOTE"
    read -p "Change remote? [y/N]: " CHANGE_REMOTE
    if [[ "$CHANGE_REMOTE" =~ ^[Yy]$ ]]; then
        git remote remove origin
    else
        echo "Keeping existing remote"
        exit 0
    fi
fi

# Get GitHub repo info
echo ""
read -p "Enter your GitHub username: " GITHUB_USER
read -p "Enter repository name [pax]: " REPO_NAME
REPO_NAME=${REPO_NAME:-pax}

echo ""
echo "Repository will be: https://github.com/$GITHUB_USER/$REPO_NAME"
read -p "Create this repository on GitHub? (you'll need to create it manually) [y/N]: " CREATE_NOW

if [[ "$CREATE_NOW" =~ ^[Yy]$ ]]; then
    echo ""
    echo "Opening GitHub repository creation page..."
    echo "After creating the repo, come back and press Enter"
    open "https://github.com/new?name=$REPO_NAME" 2>/dev/null || echo "Please visit: https://github.com/new?name=$REPO_NAME"
    read -p "Press Enter after creating the repository..."
fi

# Set remote
REMOTE_URL="https://github.com/$GITHUB_USER/$REPO_NAME.git"
git remote add origin "$REMOTE_URL" 2>/dev/null || git remote set-url origin "$REMOTE_URL"

echo ""
echo "Remote configured: $REMOTE_URL"
echo ""
echo "Next steps:"
echo "1. Add and commit files:"
echo "   git add ."
echo "   git commit -m 'Initial commit: Pax NYC camera collection system'"
echo ""
echo "2. Push to GitHub:"
echo "   git push -u origin main"
echo ""
echo "Or run: ./push_to_github.sh"

