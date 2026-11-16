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

def get_revision_from_dockerhub(image_name, tag):
    """
    Fetches the exact commit SHA of the official Overleaf release from the
    com.overleaf.ce.revision OCI label without downloading any image layers.
    """
    try:
        token_url = f"https://auth.docker.io/token?service=registry.docker.io&scope=repository:{image_name}:pull"
        req = urllib.request.Request(token_url, headers={"User-Agent": "Mozilla/5.0"})
        token_data = json.loads(urllib.request.urlopen(req, timeout=10).read().decode("utf-8"))
        token = token_data.get("token")
        if not token:
            return None

        manifest_url = f"https://registry-1.docker.io/v2/{image_name}/manifests/{tag}"
        req = urllib.request.Request(manifest_url, headers={
            "User-Agent": "Mozilla/5.0",
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.docker.distribution.manifest.v2+json, application/vnd.oci.image.manifest.v1+json, application/vnd.oci.image.index.v1+json"
        })
        manifest = json.loads(urllib.request.urlopen(req, timeout=10).read().decode("utf-8"))

        if "manifests" in manifest:
            for m in manifest["manifests"]:
                if m.get("platform", {}).get("architecture") == "amd64":
                    req = urllib.request.Request(f"https://registry-1.docker.io/v2/{image_name}/manifests/{m['digest']}", headers={
                        "User-Agent": "Mozilla/5.0",
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.docker.distribution.manifest.v2+json, application/vnd.oci.image.manifest.v1+json"
                    })
                    manifest = json.loads(urllib.request.urlopen(req, timeout=10).read().decode("utf-8"))
                    break

        config_digest = manifest.get("config", {}).get("digest")
        if not config_digest:
            return None

        blob_url = f"https://registry-1.docker.io/v2/{image_name}/blobs/{config_digest}"
        req = urllib.request.Request(blob_url, headers={
            "User-Agent": "Mozilla/5.0",
            "Authorization": f"Bearer {token}"
        })
        config_data = json.loads(urllib.request.urlopen(req, timeout=10).read().decode("utf-8"))
        revision = config_data.get("config", {}).get("Labels", {}).get("com.overleaf.ce.revision")
        return revision
    except Exception as e:
        print(f"Warning: could not fetch revision from Docker Hub for {image_name}:{tag}: {e}", file=sys.stderr)
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
        print("Usage: check_version.py <registry_image_base> <manual_version_or_empty> [manual_git_ref_or_empty] [github_output_file]")
        sys.exit(1)

    image_base = sys.argv[1].lower()
    manual_version = sys.argv[2].strip()
    manual_git_ref = sys.argv[3].strip() if len(sys.argv) > 3 else ""
    github_output = sys.argv[4] if len(sys.argv) > 4 else None

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

    # Determine exact git_ref
    if manual_git_ref:
        git_ref = manual_git_ref
        print(f"Using explicitly requested git_ref: {git_ref}")
    else:
        print(f"Resolving exact git commit from official sharelatex/sharelatex:{target_version}...")
        official_commit = get_revision_from_dockerhub("sharelatex/sharelatex", target_version)
        if official_commit:
            git_ref = official_commit
            print(f"✅ Found official release commit SHA: {git_ref}")
        else:
            git_ref = "main"
            print("⚠️ Could not detect official commit SHA, falling back to 'main'")

    print(f"Result: target_version={target_version}, needs_build={needs_build}, git_ref={git_ref}")

    if github_output:
        with open(github_output, "a") as f:
            f.write(f"version={target_version}\n")
            f.write(f"needs_build={'true' if needs_build else 'false'}\n")
            f.write(f"git_ref={git_ref}\n")

if __name__ == "__main__":
    main()
