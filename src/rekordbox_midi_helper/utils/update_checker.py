"""
Update checking utility for fucka CLI tool.

Supports two channels:
- stable: Check GitHub Releases for version tags
- dev: Check latest commits on development branch
"""

import json
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, Dict, Any
from packaging.version import Version


class UpdateChecker:
    """Check for updates from GitHub"""

    REPO_OWNER = "LiTLiTschi"
    REPO_NAME = "fuck-alphatheta"
    DEFAULT_DEV_BRANCH = "claude/rekordbox-midi-python-script-FuBNl"
    CACHE_FILENAME = "update_cache.json"
    DEFAULT_CHECK_INTERVAL = 24  # hours

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize update checker.

        Args:
            config_dir: Configuration directory path (default: ~/.config/fucka)
        """
        if config_dir is None:
            from .config_path import ensure_config_dir
            config_dir = ensure_config_dir()

        self.config_dir = Path(config_dir)
        self.cache_file = self.config_dir / self.CACHE_FILENAME

    def check_for_updates(
        self,
        current_version: str,
        channel: str = "dev",
        branch: Optional[str] = None,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Check for updates.

        Args:
            current_version: Current version string (e.g., "2.0.0")
            channel: Update channel ("stable" or "dev")
            branch: Git branch for dev channel (default: DEFAULT_DEV_BRANCH)
            force: Force check even if cache is fresh

        Returns:
            Dictionary with update information:
            {
                "update_available": bool,
                "current_version": str,
                "latest_version": str,
                "release_url": str,
                "release_notes": str,
                "published_at": str,
                "channel": str
            }
        """
        # Check cache first
        if not force:
            cached = self.get_cached_update_info()
            if cached and not self.is_cache_expired(cached):
                return cached

        # Fetch fresh data
        if channel == "stable":
            info = self._check_stable_channel(current_version)
        else:  # dev channel
            branch = branch or self.DEFAULT_DEV_BRANCH
            info = self._check_dev_channel(current_version, branch)

        # Save to cache
        if info:
            self.save_update_cache(info)

        return info

    def _check_stable_channel(self, current_version: str) -> Dict[str, Any]:
        """Check GitHub Releases for latest stable version"""
        try:
            release_info = self._fetch_latest_release()
            if not release_info:
                return self._create_no_update_info(current_version, "stable")

            latest_version = release_info["tag_name"].lstrip("v")

            # Compare versions
            try:
                current = Version(current_version)
                latest = Version(latest_version)
                update_available = latest > current
            except Exception:
                # If version parsing fails, compare as strings
                update_available = latest_version != current_version

            return {
                "update_available": update_available,
                "current_version": current_version,
                "latest_version": latest_version,
                "release_url": release_info.get("html_url", ""),
                "release_notes": release_info.get("body", "No release notes available."),
                "published_at": release_info.get("published_at", ""),
                "channel": "stable",
                "last_check_timestamp": int(time.time()),
                "check_interval_hours": self.DEFAULT_CHECK_INTERVAL
            }
        except Exception as e:
            print(f"Warning: Could not check for updates: {e}")
            return self._create_no_update_info(current_version, "stable", error=str(e))

    def _check_dev_channel(self, current_version: str, branch: str) -> Dict[str, Any]:
        """Check GitHub commits for latest dev version"""
        try:
            commit_info = self._fetch_latest_commit(branch)
            if not commit_info:
                return self._create_no_update_info(current_version, "dev")

            latest_sha = commit_info["sha"][:8]  # Short SHA
            commit_date = commit_info.get("commit", {}).get("committer", {}).get("date", "")
            commit_message = commit_info.get("commit", {}).get("message", "").split("\n")[0]

            # For dev channel, we show commit info
            # Update is "available" if there's a newer commit (we can't easily tell without tracking)
            # So we just show the latest commit info

            return {
                "update_available": True,  # Always suggest checking for dev channel
                "current_version": current_version,
                "latest_version": f"{current_version}+{latest_sha}",
                "release_url": f"https://github.com/{self.REPO_OWNER}/{self.REPO_NAME}/commit/{commit_info['sha']}",
                "release_notes": f"Latest commit: {commit_message}",
                "published_at": commit_date,
                "channel": "dev",
                "branch": branch,
                "latest_commit_sha": commit_info["sha"],
                "last_check_timestamp": int(time.time()),
                "check_interval_hours": self.DEFAULT_CHECK_INTERVAL
            }
        except Exception as e:
            print(f"Warning: Could not check for updates: {e}")
            return self._create_no_update_info(current_version, "dev", error=str(e))

    def _fetch_latest_release(self) -> Optional[Dict[str, Any]]:
        """Fetch latest release from GitHub Releases API"""
        url = f"https://api.github.com/repos/{self.REPO_OWNER}/{self.REPO_NAME}/releases/latest"
        return self._fetch_json(url)

    def _fetch_latest_commit(self, branch: str) -> Optional[Dict[str, Any]]:
        """Fetch latest commit from GitHub Commits API"""
        url = f"https://api.github.com/repos/{self.REPO_OWNER}/{self.REPO_NAME}/commits/{branch}"
        return self._fetch_json(url)

    def _fetch_json(self, url: str, timeout: int = 5) -> Optional[Dict[str, Any]]:
        """Fetch JSON from URL with timeout"""
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None  # Not found
            raise
        except Exception:
            raise

    def _create_no_update_info(
        self,
        current_version: str,
        channel: str,
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create info dict for no update available"""
        return {
            "update_available": False,
            "current_version": current_version,
            "latest_version": current_version,
            "release_url": "",
            "release_notes": "",
            "published_at": "",
            "channel": channel,
            "error": error,
            "last_check_timestamp": int(time.time()),
            "check_interval_hours": self.DEFAULT_CHECK_INTERVAL
        }

    def get_cached_update_info(self) -> Optional[Dict[str, Any]]:
        """Read cached update info from file"""
        try:
            if not self.cache_file.exists():
                return None

            with open(self.cache_file, "r") as f:
                return json.load(f)
        except Exception:
            return None

    def save_update_cache(self, info: Dict[str, Any]) -> None:
        """Save update info to cache file"""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)

            with open(self.cache_file, "w") as f:
                json.dump(info, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save update cache: {e}")

    def is_cache_expired(self, cached_info: Dict[str, Any]) -> bool:
        """Check if cached info is expired"""
        try:
            last_check = cached_info.get("last_check_timestamp", 0)
            interval_hours = cached_info.get("check_interval_hours", self.DEFAULT_CHECK_INTERVAL)
            interval_seconds = interval_hours * 3600

            return (time.time() - last_check) > interval_seconds
        except Exception:
            return True  # If any error, consider expired

    def clear_cache(self) -> None:
        """Clear update cache"""
        try:
            if self.cache_file.exists():
                self.cache_file.unlink()
        except Exception as e:
            print(f"Warning: Could not clear cache: {e}")
