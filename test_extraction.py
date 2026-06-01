# Replace Old Files Without Losing Secrets

GitHub secrets are not files. They live here:

```text
Settings -> Secrets and variables -> Actions
```

Deleting repo files does not delete these secrets.

Fast beginner method:

1. Download this zip.
2. Extract it.
3. Open GitHub repo.
4. Click `Add file -> Upload files`.
5. Drag everything from the extracted folder.
6. Commit changes.
7. Run `Trump Market Alert - cleanup old wrong files`.
8. Run `Trump Market Alert - manual test`.

Your old nested wrong folder will be removed by the cleanup workflow.
