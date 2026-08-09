#!/usr/bin/env python3
"""Generate an AltStore/SideStore-compatible source JSON for Dopamine.

Fetches the latest releases of opa334/Dopamine from the GitHub API and
writes an apps.json source file. Version metadata (version, build version,
minimum OS) is extracted from each release's actual .ipa and cached in
ipa-metadata.json, so IPAs are only downloaded once per release.

Works with Python 3.8+ (stdlib only, no pip dependencies).

Usage:
    python3 generate.py --source-url https://example.com/apps.json
    python3 generate.py --source-url ... --stable-only --no-news

Optional environment variable:
    GITHUB_TOKEN    a GitHub personal access token (raises the API rate
                    limit from 60 to 5000 requests/hour)
"""

import argparse
import json
import os
import plistlib
import shutil
import sys
import tempfile
import urllib.request
import zipfile

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


def download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": "dopamine-altstore-source"})
    with urllib.request.urlopen(req, timeout=120) as resp, open(dest, "wb") as fh:
        shutil.copyfileobj(resp, fh)


def extract_ipa_metadata(ipa_path):
    """Read (short version, build version, minimum OS) from the IPA's Info.plist."""
    with zipfile.ZipFile(ipa_path) as zf:
        infos = [
            n for n in zf.namelist()
            if n.startswith("Payload/") and n.endswith(".app/Info.plist")
        ]
        if not infos:
            raise ValueError("no Payload/*.app/Info.plist found in IPA")
        with zf.open(infos[0]) as fh:
            plist = plistlib.load(fh)
    return (
        str(plist.get("CFBundleShortVersionString") or ""),
        str(plist.get("CFBundleVersion") or ""),
        str(plist.get("MinimumOSVersion") or ""),
    )


def get_release_metadata(release, ipa, cache, tmpdir):
    release_id = str(release["id"])
    if release_id in cache:
        return cache[release_id]
    tmp = os.path.join(tmpdir, "dopamine-download.ipa")
    print("  downloading {} ({:.1f} MB)...".format(
        release["tag_name"], ipa["size"] / 1024 / 1024))
    download(ipa["browser_download_url"], tmp)
    try:
        short, build, minos = extract_ipa_metadata(tmp)
    finally:
        os.remove(tmp)
    meta = {"short": short, "build": build, "minos": minos}
    cache[release_id] = meta
    return meta


def build_source(releases, args, existing, cache, tmpdir):
    include_prerelease = not args.stable_only
    selected = [
        r for r in releases
        if (include_prerelease or not r["prerelease"]) and release_ipa(r)
    ]

    entries_by_tag = {}
    for release in selected:
        ipa = release_ipa(release)
        meta = get_release_metadata(release, ipa, cache, tmpdir)
        entry = {
            "version": meta["short"] or release["tag_name"],
            "date": release["published_at"],
            "versionDate": release["published_at"],
            "localizedDescription": version_description(release)
            or "New Dopamine release.",
            "downloadURL": ipa["browser_download_url"],
            "size": ipa["size"],
            "minOSVersion": meta["minos"] or MIN_IOS,
        }
        if meta["build"]:
            entry["buildVersion"] = meta["build"]
        entries_by_tag[release["tag_name"]] = entry

    ordered = sorted(
        entries_by_tag.values(),
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
            news.append(
                {
                    "identifier": identifier,
                    "appID": "com.opa334.Dopamine",
                    "title": "Dopamine {} released".format(release["tag_name"]),
                    "caption": version_description(release) or "New release",
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


def version_description(release):
    body = (release.get("body") or "").strip()
    if not body:
        return None
    first = body.splitlines()[0].strip().strip("* -")
    if len(first) > 200:
        first = first[:200].rsplit(" ", 1)[0] + "..."
    return first


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
    parser.add_argument(
        "--metadata",
        default="ipa-metadata.json",
        help="IPA metadata cache file (default: ipa-metadata.json)",
    )
    parser.add_argument("--owner", default=DEFAULT_OWNER)
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--icon-url", default=APP_ICON_URL)
    parser.add_argument(
        "--stable-only",
        action="store_true",
        help="Exclude pre-release (beta) versions",
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

    cache = {}
    if os.path.exists(args.metadata):
        with open(args.metadata, encoding="utf-8") as fh:
            cache = json.load(fh)

    existing = {}
    if os.path.exists(args.out):
        with open(args.out, encoding="utf-8") as fh:
            existing = json.load(fh)

    with tempfile.TemporaryDirectory(prefix="dopamine-source-") as tmpdir:
        source = build_source(releases, args, existing, cache, tmpdir)

        tmp = args.out + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(source, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        os.replace(tmp, args.out)

        tmp = args.metadata + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(cache, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        os.replace(tmp, args.metadata)

    print("Wrote {} with {} version(s), latest: {}".format(
        args.out, len(source["apps"][0]["versions"]),
        source["apps"][0]["version"],
    ))


if __name__ == "__main__":
    main()
