# Git Push Cheat Sheet

Use this from the project folder:

```bash
cd "d:\AI projects\documind-rag"
git status
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin <your-github-repo-url>   # only if needed
git push -u origin main
```

## Common push after setup

```bash
git add .
git commit -m "Update code"
git push
```

## Useful checks

```bash
git status
git log --oneline -n 5
git remote -v
```

## If Git says “nothing to commit”

```bash
git status
git add .
```

## If the repo is already connected

```bash
git add .
git commit -m "Your message"
git push
```

> Typical workflow: add → commit → push.
