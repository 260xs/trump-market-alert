name: Trump Market Alert - keep scheduled workflows active

on:
  workflow_dispatch:
  schedule:
    - cron: "19 7 1,15 * *"

permissions:
  contents: write

jobs:
  keepalive:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Create harmless repository activity
        shell: bash
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git commit --allow-empty -m "Keep scheduled workflows active"
          git push
