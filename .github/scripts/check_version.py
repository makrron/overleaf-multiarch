#!/usr/bin/env python3
import urllib.request
import json
import re
import sys
import subprocess

def get_latest_upstream_version():
    url = "https://registry.hub.docker.com/v2/repositories/sharelatex/sharelatex/tags?page_size=100"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        response = urllib.request.urlopen(req, timeout=15)
        data = json.loads(response.read().decode("utf-8"))
        semver_regex = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
        valid_versions = []
        for r in data.get("results", []):
            tag = r.get("name", "")
            if semver_regex.match(tag):
                parts = tuple(map(int, tag.split(".")))
                valid_versions.append((parts, tag))
        valid_versions.sort(reverse=True)
        if valid_versions:
            return valid_versions[0][1]
    except Exception as e:
        print(f"Error querying Docker Hub: {e}", file=sys.stderr)
    return None

def check_image_exists_with_both_archs(image_tag):
    try:
        res = subprocess.run(
            ["docker", "buildx", "imagetools", "inspect", image_tag],
            capture_output=True,
            text=True,
            check=False
        )
        if res.returncode != 0:
            return False
        output = res.stdout
        return ("linux/amd64" in output) and ("linux/arm64" in output)
    except Exception as e:
        print(f"Error checking image {image_tag}: {e}", file=sys.stderr)
        return False

def main():
    if len(sys.argv) < 3:
        print("Usage: check_version.py <registry_image_base> <manual_version_or_empty> [github_output_file]")
        sys.exit(1)

    image_base = sys.argv[1].lower()
    manual_version = sys.argv[2].strip()
    github_output = sys.argv[3] if len(sys.argv) > 3 else None

    if manual_version:
        print(f"Manual build requested for version: {manual_version}")
        target_version = manual_version
        needs_build = True
    else:
        print("Querying Docker Hub API for latest stable sharelatex/sharelatex tags...")
        latest_tag = get_latest_upstream_version()
        if not latest_tag:
            print("Failed to query latest version from Docker Hub", file=sys.stderr)
            sys.exit(1)

        print(f"Latest upstream Overleaf version: {latest_tag}")
        target_version = latest_tag

        full_image_tag = f"{image_base}:{target_version}"
        print(f"Checking if {full_image_tag} already exists with both amd64 and arm64...")
        if check_image_exists_with_both_archs(full_image_tag):
            print(f"✅ Version {target_version} is already published with multi-arch (amd64 & arm64). No build needed.")
            needs_build = False
        else:
            print(f"🚀 New version or incomplete multi-arch image ({target_version}). Triggering build!")
            needs_build = True

    print(f"Result: target_version={target_version}, needs_build={needs_build}")

    if github_output:
        with open(github_output, "a") as f:
            f.write(f"version={target_version}\n")
            f.write(f"needs_build={'true' if needs_build else 'false'}\n")

if __name__ == "__main__":
    main()
