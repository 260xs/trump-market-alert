name: Trump Market Alert - cleanup old wrong files

on:
  workflow_dispatch:

permissions:
  contents: write

jobs:
  cleanup:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Remove old mistaken files/folders
        shell: bash
        run: |
          rm -rf ".github/workflows/.github" || true
          rm -f Dockerfile Procfile || true
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add -A
          if git diff --cached --quiet; then
            echo "Nothing to clean."
          else
            git commit -m "Clean old workflow files"
            git push
          fi
