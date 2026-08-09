# Dopamine — AltStore / SideStore Source

Automatically updated [AltStore/SideStore](https://sidestore.io) source for the
[Dopamine](https://github.com/opa334/Dopamine) jailbreak. New releases are picked up
automatically — no more downloading and sideloading IPAs manually.

## Add to SideStore / AltStore

1. Open SideStore (or AltStore) → **Sources** → **+**
2. Add this URL:

   ```
   https://shadowthijs.github.io/dopamine-altstore-repo/apps.json
   ```

3. Install **Dopamine** from the source.

Updates appear automatically on the next refresh.

## How it works

A GitHub Actions workflow (`.github/workflows/update-source.yml`) checks for new
Dopamine releases every 6 hours, regenerates `apps.json` with
[`generate.py`](generate.py), and commits it. GitHub Pages serves the file. That's it —
no servers, no cron, nothing to maintain.

## Run the update manually

**Actions** → **Update AltStore source** → **Run workflow**. (Or just push any change
to `master` — the workflow runs on push too.)

## Files

| File | Purpose |
| ---- | ------- |
| `apps.json` | The source file served via GitHub Pages |
| `generate.py` | Generates `apps.json` from the GitHub releases API (Python 3.8+, no dependencies) |
| `ipa-metadata.json` | Cache of real version/build-number data extracted from each IPA (so IPAs are only downloaded once) |
| `.github/workflows/update-source.yml` | Auto-updates `apps.json` every 6 hours |

## Notes

- IPAs are downloaded from GitHub's own release CDN — nothing is mirrored.
- Beta versions are included by default and appear in the version list (e.g. `2.5b4`).
  Run `python3 generate.py --help` for options (e.g. `--stable-only` to exclude betas).
- Dopamine is developed by [opa334](https://github.com/opa334), not by this repo's
  maintainer. This repo only mirrors release metadata.
