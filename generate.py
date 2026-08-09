#!/usr/bin/env python3
"""Generate an AltStore/SideStore-compatible source JSON for Dopamine.

Fetches the latest releases of opa334/Dopamine from the GitHub API and
writes an apps.json source file. Existing version history is merged so it
is preserved across runs.

Works with Python 3.8+ (stdlib only, no pip dependencies).

Usage:
    python3 generate.py --source-url https://example.com/apps.json
    python3 generate.py --source-url ... --prereleases --no-news

Optional environment variable:
    GITHUB_TOKEN    a GitHub personal access token (raises the API rate
                    limit from 60 to 5000 requests/hour)
"""

import argparse
import json
import os
import sys
import urllib.request

DEFAULT_OWNER = "opa334"
DEFAULT_REPO = "Dopamine"
SOURCE_IDENTIFIER = "com.opa334.dopamine-source"
SOURCE_HEADER_URL = "https://github.com/opa334/Dopamine/assets/52459150/ed04dd3e-d879-456d-9aa3-d4ed44819c7e"
APP_ICON_URL = (
    "https://raw.githubusercontent.com/opa334/Dopamine/3.x/"
    "Application/Dopamine/Assets.xcassets/AppIcon.appiconset/Icon-60@3x.png"
)
APP_DESCRIPTION = (
    "Dopamine is a rootless semi-untethered jailbreak for iOS 15.0 - 17.3.1 "
    "(arm64e), iOS 15.0 - 18.7.1 and 26.0 - 26.0.1 (A12/A13) and iOS 15.0 - "
    "18.7.1 (arm64).\n\n"
    "Official website: https://ellekit.space/dopamine/\n"
    "Source code: https://github.com/opa334/Dopamine"
)
APP_SUBTITLE = "A rootless semi-untethered jailbreak for iOS 15.0 - 18.7.1"
TINT_COLOR = "#7C4DFF"
MIN_IOS = "15.0"


def api_get(url, token):
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "dopamine-altstore-source")
    if token:
        req.add_header("Authorization", "Bearer {}".format(token))
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def fetch_releases(owner, repo, token):
    releases = []
    for page in (1, 2):
        url = "https://api.github.com/repos/{}/{}/releases?per_page=100&page={}".format(
            owner, repo, page
        )
        batch = api_get(url, token)
        if not batch:
            break
        releases.extend(batch)
    return releases


def release_ipa(release):
    for asset in release.get("assets", []):
        if asset["name"].lower().endswith(".ipa"):
            return asset
    return None


def version_description(release):
    body = (release.get("body") or "").strip()
    if not body:
        return None
    first = body.splitlines()[0].strip().strip("* -")
    if len(first) > 200:
        first = first[:200].rsplit(" ", 1)[0] + "..."
    return first


def build_source(releases, args, existing):
    include_prerelease = args.prereleases
    selected = [
        r for r in releases
        if (include_prerelease or not r["prerelease"]) and release_ipa(r)
    ]

    versions = {}
    for release in selected:
        ipa = release_ipa(release)
        if not ipa:
            continue
        versions[release["tag_name"]] = {
            "version": release["tag_name"],
            "buildVersion": str(release["id"]),
            "date": release["published_at"],
            "versionDate": release["published_at"],
            "localizedDescription": version_description(release)
            or "New Dopamine release.",
            "downloadURL": ipa["browser_download_url"],
            "size": ipa["size"],
            "minOSVersion": MIN_IOS,
        }

    old_versions = (existing.get("apps") or [{}])[0].get("versions") or []
    for entry in old_versions:
        versions.setdefault(entry["version"], entry)

    ordered = sorted(
        versions.values(),
        key=lambda v: v["date"],
        reverse=True,
    )

    latest = ordered[0]
    app = {
        "name": "Dopamine",
        "bundleIdentifier": "com.opa334.Dopamine",
        "developerName": "opa334",
        "subtitle": APP_SUBTITLE,
        "localizedDescription": APP_DESCRIPTION,
        "iconURL": args.icon_url,
        "tintColor": TINT_COLOR,
        "category": "utilities",
        "beta": False,
        "version": latest["version"],
        "versionDate": latest["date"],
        "downloadURL": latest["downloadURL"],
        "size": latest["size"],
        "versions": ordered,
    }

    news = []
    if args.news:
        seen = {item["identifier"] for item in existing.get("news") or []}
        for release in selected:
            identifier = "dopamine-{}".format(release["tag_name"])
            if identifier in seen:
                continue
            seen.add(identifier)
            desc = version_description(release) or "New release"
            news.append(
                {
                    "identifier": identifier,
                    "appID": "com.opa334.Dopamine",
                    "title": "Dopamine {} released".format(release["tag_name"]),
                    "caption": desc,
                    "date": release["published_at"],
                    "tintColor": TINT_COLOR,
                    "notify": False,
                    "url": release["html_url"],
                }
            )

    source = {
        "name": "Dopamine",
        "subtitle": APP_SUBTITLE,
        "description": APP_DESCRIPTION,
        "identifier": SOURCE_IDENTIFIER,
        "sourceURL": args.source_url,
        "iconURL": args.icon_url,
        "headerURL": SOURCE_HEADER_URL,
        "website": "https://ellekit.space/dopamine/",
        "tintColor": TINT_COLOR,
        "nsfw": False,
        "featuredApps": ["com.opa334.Dopamine"],
        "apps": [app],
        "news": news + (existing.get("news") or []),
    }
    return source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-url",
        required=True,
        help="Public URL where this apps.json will be hosted, e.g. "
        "https://user.github.io/dopamine-repo/apps.json",
    )
    parser.add_argument(
        "--out", default="apps.json", help="Output file (default: apps.json)"
    )
    parser.add_argument("--owner", default=DEFAULT_OWNER)
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--icon-url", default=APP_ICON_URL)
    parser.add_argument(
        "--prereleases",
        action="store_true",
        help="Also include pre-release (beta) versions",
    )
    parser.add_argument(
        "--no-news",
        dest="news",
        action="store_false",
        help="Do not add news items for new releases",
    )
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    try:
        releases = fetch_releases(args.owner, args.repo, token)
    except Exception as exc:
        print("ERROR: could not fetch releases from GitHub: {}".format(exc), file=sys.stderr)
        sys.exit(1)

    existing = {}
    if os.path.exists(args.out):
        with open(args.out, encoding="utf-8") as fh:
            existing = json.load(fh)

    source = build_source(releases, args, existing)

    tmp = args.out + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(source, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    os.replace(tmp, args.out)

    print("Wrote {} with {} version(s), latest: {}".format(
        args.out, len(source["apps"][0]["versions"]),
        source["apps"][0]["version"],
    ))


if __name__ == "__main__":
    main()
