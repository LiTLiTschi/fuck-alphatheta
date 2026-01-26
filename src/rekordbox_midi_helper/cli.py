"""
CLI interface for Rekordbox MIDI Helper - 'fucka' command.

Provides subcommands:
- fucka config: Run interactive configuration wizard
- fucka start: Start the application in background
- fucka stop: Stop the running application
- fucka status: Check if application is running
- fucka run: Run in foreground (for debugging)

Usage:
    fucka config
    fucka start [--config path/to/config.yaml] [--debug]
    fucka stop
    fucka status
    fucka run [--config path/to/config.yaml] [--debug]
"""

import sys
import os
import argparse
import subprocess
import time
import signal
import shutil
from pathlib import Path
from typing import Optional

import psutil
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

# PID and log file location
PID_FILE = Path.home() / ".config" / "fucka" / "fucka.pid"
LOG_FILE = Path.home() / ".config" / "fucka" / "fucka.log"


def print_info(text: str):
    """Print info message."""
    print(f"{Fore.GREEN}ℹ {text}{Style.RESET_ALL}")


def print_error(text: str):
    """Print error message."""
    print(f"{Fore.RED}✗ {text}{Style.RESET_ALL}")


def print_success(text: str):
    """Print success message."""
    print(f"{Fore.GREEN}✓ {text}{Style.RESET_ALL}")


def print_warning(text: str):
    """Print warning message."""
    print(f"{Fore.YELLOW}⚠ {text}{Style.RESET_ALL}")


def ensure_fucka_dir():
    """Ensure ~/.config/fucka directory exists."""
    fucka_dir = Path.home() / ".config" / "fucka"
    fucka_dir.mkdir(parents=True, exist_ok=True)
    return fucka_dir


def is_running() -> Optional[int]:
    """
    Check if the application is running.

    Returns:
        PID if running, None otherwise
    """
    if not PID_FILE.exists():
        return None

    try:
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())

        # Check if process is actually running
        if psutil.pid_exists(pid):
            try:
                proc = psutil.Process(pid)
                # Check if it's actually our process
                cmdline = ' '.join(proc.cmdline())
                if 'fucka' in cmdline or 'rekordbox_midi_helper' in cmdline:
                    return pid
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        # PID file exists but process is not running - clean up
        PID_FILE.unlink()
        return None

    except Exception as e:
        print_error(f"Error checking process status: {e}")
        return None


def write_pid(pid: int):
    """Write PID to file."""
    ensure_fucka_dir()
    with open(PID_FILE, 'w') as f:
        f.write(str(pid))


def remove_pid():
    """Remove PID file."""
    if PID_FILE.exists():
        PID_FILE.unlink()


def cmd_config(args):
    """Run the configuration TUI."""
    from .tui import RekordboxConfigApp
    from .utils.config_path import ensure_config_exists

    # Use ~/.config/fucka/config.yaml (or custom path if provided)
    if hasattr(args, 'config') and args.config:
        config_path = args.config
    else:
        config_path = str(ensure_config_exists())

    app = RekordboxConfigApp(config_path)

    try:
        app.run()
    except KeyboardInterrupt:
        print("\n")
        print_warning("Configuration cancelled")
        sys.exit(1)


def cmd_start(args):
    """Start the application in background."""
    from .utils.config_path import get_config_path

    # Check if already running
    pid = is_running()
    if pid:
        print_warning(f"Application is already running (PID: {pid})")
        print_info(f"Use 'fucka stop' to stop it first")
        sys.exit(1)

    # Use ~/.config/fucka/config.yaml (or custom path if provided)
    if hasattr(args, 'config') and args.config:
        config_path = args.config
    else:
        config_path = str(get_config_path())

    # Check if config exists
    if not os.path.exists(config_path):
        print_error(f"Configuration file not found: {config_path}")
        print_info("Run 'fucka config' to create a configuration file")
        sys.exit(1)

    # Start application in background
    print_info("Starting Rekordbox MIDI Helper in background...")

    ensure_fucka_dir()

    # Build command
    cmd = [
        sys.executable,
        '-m',
        'rekordbox_midi_helper.main',
        '--config', config_path
    ]

    if args.debug:
        cmd.append('--debug')

    # Start process in background
    try:
        if os.name == 'nt':  # Windows
            # Use CREATE_NEW_PROCESS_GROUP to detach from parent
            CREATE_NEW_PROCESS_GROUP = 0x00000200
            DETACHED_PROCESS = 0x00000008

            log_file = open(LOG_FILE, 'w')

            proc = subprocess.Popen(
                cmd,
                stdout=log_file,
                stderr=log_file,
                creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
                close_fds=True
            )
        else:  # Linux/Mac
            log_file = open(LOG_FILE, 'w')

            proc = subprocess.Popen(
                cmd,
                stdout=log_file,
                stderr=log_file,
                start_new_session=True,
                close_fds=True
            )

        # Give it a moment to start
        time.sleep(2)

        # Check if process started successfully
        if proc.poll() is None:
            # Process is running
            write_pid(proc.pid)
            print_success(f"Application started successfully (PID: {proc.pid})")
            print_info(f"Logs: {LOG_FILE}")

            # If --monitor flag is set, start live monitor
            if hasattr(args, 'monitor') and args.monitor:
                print()
                print_info("Starting live monitor...")
                print_info("Press Ctrl+C to stop monitor (app will continue running)")
                print()
                time.sleep(1)

                from .live_monitor import main as live_monitor_main
                try:
                    live_monitor_main(config_path)
                except KeyboardInterrupt:
                    print()
                    print_info("Monitor stopped")
                print()
                print_info(f"Application still running (PID: {proc.pid})")
                print_info(f"Use 'fucka monitor' to show monitor again")
                print_info(f"Use 'fucka stop' to stop the application")
            else:
                print_info(f"Use 'fucka status' to check status")
                print_info(f"Use 'fucka monitor' to show live monitor")
                print_info(f"Use 'fucka stop' to stop the application")
        else:
            print_error("Application failed to start")
            print_info(f"Check logs at: {LOG_FILE}")
            sys.exit(1)

    except Exception as e:
        print_error(f"Failed to start application: {e}")
        sys.exit(1)


def cmd_stop(args):
    """Stop the running application."""
    pid = is_running()

    if not pid:
        print_warning("Application is not running")
        sys.exit(0)

    print_info(f"Stopping application (PID: {pid})...")

    try:
        proc = psutil.Process(pid)

        # Try graceful shutdown first
        if os.name == 'nt':  # Windows
            proc.terminate()
        else:  # Linux/Mac
            proc.send_signal(signal.SIGTERM)

        # Wait up to 5 seconds for graceful shutdown
        try:
            proc.wait(timeout=5)
            print_success("Application stopped successfully")
        except psutil.TimeoutExpired:
            # Force kill if graceful shutdown failed
            print_warning("Graceful shutdown failed, forcing termination...")
            proc.kill()
            proc.wait(timeout=2)
            print_success("Application terminated")

        remove_pid()

    except psutil.NoSuchProcess:
        print_warning("Process not found (may have already stopped)")
        remove_pid()
    except Exception as e:
        print_error(f"Error stopping application: {e}")
        sys.exit(1)


def cmd_status(args):
    """Check application status."""
    pid = is_running()

    if pid:
        try:
            proc = psutil.Process(pid)
            cpu_percent = proc.cpu_percent(interval=0.1)
            memory_info = proc.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024

            print_success(f"Application is running")
            print(f"  PID: {pid}")
            print(f"  CPU: {cpu_percent:.1f}%")
            print(f"  Memory: {memory_mb:.1f} MB")
            print(f"  Status: {proc.status()}")

            # Show uptime
            create_time = proc.create_time()
            uptime_seconds = time.time() - create_time
            uptime_minutes = int(uptime_seconds / 60)
            uptime_hours = int(uptime_minutes / 60)
            uptime_minutes = uptime_minutes % 60

            print(f"  Uptime: {uptime_hours}h {uptime_minutes}m")

            if LOG_FILE.exists():
                print(f"  Logs: {LOG_FILE}")

        except Exception as e:
            print_error(f"Error getting process info: {e}")
            sys.exit(1)
    else:
        print_info("Application is not running")
        print_info("Use 'fucka start' to start the application")


def cmd_run(args):
    """Run the application in foreground (for debugging)."""
    from .main import RekordboxMIDIHelper
    from .utils.config_path import get_config_path

    # Use ~/.config/fucka/config.yaml (or custom path if provided)
    if args.config:
        config_path = args.config
    else:
        config_path = str(get_config_path())

    if not os.path.exists(config_path):
        print_error(f"Configuration file not found: {config_path}")
        print_info("Run 'fucka config' to create a configuration file")
        sys.exit(1)

    print_info("Starting Rekordbox MIDI Helper (foreground mode)...")
    print_info("Press Ctrl+C to stop")
    print()

    # Create and run application
    app = RekordboxMIDIHelper(
        config_path=config_path,
        debug=args.debug
    )

    try:
        app.run()
    except KeyboardInterrupt:
        print("\n")
        print_info("Shutting down...")
        app.shutdown()


def cmd_logs(args):
    """Show application logs."""
    if not LOG_FILE.exists():
        print_warning(f"No log file found at: {LOG_FILE}")
        sys.exit(1)

    # Show tail of log file
    try:
        with open(LOG_FILE, 'r') as f:
            lines = f.readlines()

        # Show last N lines
        num_lines = args.lines if hasattr(args, 'lines') else 50
        tail_lines = lines[-num_lines:]

        print(f"{Fore.CYAN}Showing last {len(tail_lines)} lines of {LOG_FILE}:{Style.RESET_ALL}\n")

        for line in tail_lines:
            print(line.rstrip())

        # If follow mode
        if hasattr(args, 'follow') and args.follow:
            print(f"\n{Fore.CYAN}Following log file (Ctrl+C to stop)...{Style.RESET_ALL}\n")
            try:
                with open(LOG_FILE, 'r') as f:
                    # Seek to end
                    f.seek(0, 2)
                    while True:
                        line = f.readline()
                        if line:
                            print(line.rstrip())
                        else:
                            time.sleep(0.1)
            except KeyboardInterrupt:
                print()

    except Exception as e:
        print_error(f"Error reading log file: {e}")
        sys.exit(1)


def cmd_monitor(args):
    """Show live monitor display."""
    from .utils.config_path import get_config_path
    from .live_monitor import main as live_monitor_main

    # Use ~/.config/fucka/config.yaml (or custom path if provided)
    if args.config:
        config_path = args.config
    else:
        config_path = str(get_config_path())

    if not os.path.exists(config_path):
        print_error(f"Configuration file not found: {config_path}")
        print_info("Run 'fucka config' to create a configuration file")
        sys.exit(1)

    live_monitor_main(config_path)


def cmd_update(args):
    """Update fucka to the latest version from GitHub."""
    from . import __version__ as current_version
    from .utils.update_checker import UpdateChecker
    from .utils.config_path import ensure_fucka_dir

    # Determine channel and branch
    channel = "dev" if args.dev or args.branch else "dev"  # Default to dev for now
    branch = args.branch if hasattr(args, 'branch') and args.branch else 'claude/rekordbox-midi-python-script-FuBNl'

    # Check for updates first
    try:
        print_info("Checking for updates...")
        checker = UpdateChecker()
        update_info = checker.check_for_updates(
            current_version=current_version,
            channel=channel,
            branch=branch,
            force=True  # Always force check on manual update command
        )
    except Exception as e:
        print_warning(f"Could not check for updates: {e}")
        if not args.yes:
            response = input("Continue with update anyway? [y/N]: ")
            if response.lower() != 'y':
                print_info("Update cancelled")
                return
        update_info = None

    # If --check flag, just display info and exit
    if hasattr(args, 'check') and args.check:
        print()
        _display_update_info(update_info, current_version)
        return

    # Display update information
    if update_info:
        print()
        _display_update_info(update_info, current_version)
        print()

        # Prompt for confirmation unless --yes
        if not args.yes:
            if channel == "dev":
                response = input("Update to latest development version? [Y/n]: ")
            else:
                response = input("Continue with update? [Y/n]: ")

            if response.lower() == 'n':
                print_info("Update cancelled")
                return

    # Perform update
    print()
    print_info("Updating fucka from GitHub...")

    # Build install command
    url = f"git+https://github.com/LiTLiTschi/fuck-alphatheta.git@{branch}"

    try:
        # Check if uv is available
        uv_path = shutil.which("uv")

        # Determine install flags
        if args.force:
            install_flag = "--force-reinstall"  # Old behavior: reinstall all deps
        else:
            install_flag = "--upgrade"  # New behavior: only update fucka

        if os.name == 'nt':  # Windows
            # On Windows, fucka.exe cannot update itself while running
            # Solution: Create a batch script that runs after fucka exits

            print_info(f"Detected Windows - creating update script")

            # Create update script
            ensure_fucka_dir()
            update_script = Path.home() / ".config" / "fucka" / "update_fucka.bat"

            if uv_path:
                install_cmd = f'uv pip install {install_flag} "{url}"'
            else:
                install_cmd = f'"{sys.executable}" -m pip install {install_flag} "{url}"'

            batch_content = f'''@echo off
echo Updating fucka from branch: {branch}
echo.
timeout /t 2 /nobreak >nul
{install_cmd}
if %ERRORLEVEL% EQU 0 (
    echo.
    echo Update completed successfully!
    echo Run 'fucka --version' to check the new version
) else (
    echo.
    echo Update failed!
)
echo.
pause
del "%~f0"
'''

            update_script.write_text(batch_content)

            print_info(f"Starting update script...")
            print_info(f"Current version: {current_version}")
            print()
            print_warning("This window will now close and the update will run in a new window")
            print_info("The update window will close automatically when done")

            # Start the batch script detached
            CREATE_NEW_PROCESS_GROUP = 0x00000200
            DETACHED_PROCESS = 0x00000008

            subprocess.Popen(
                ['cmd', '/c', 'start', 'cmd', '/c', str(update_script)],
                creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
                close_fds=True
            )

            # Exit immediately so the .exe can be updated
            sys.exit(0)

        else:  # Linux/Mac
            # On Linux/Mac we can update directly
            if uv_path:
                print_info(f"Using uv to install from branch: {branch}")
                cmd = ["uv", "pip", "install", install_flag, url]
            else:
                print_info(f"Using pip to install from branch: {branch}")
                cmd = [sys.executable, "-m", "pip", "install", install_flag, url]

            print_info(f"Running: {' '.join(cmd)}")

            result = subprocess.run(cmd, capture_output=False)

            if result.returncode == 0:
                print()
                print_success("Update completed successfully!")

                # Get new version
                try:
                    version_result = subprocess.run(
                        [sys.executable, "-m", "rekordbox_midi_helper.cli", "--version"],
                        capture_output=True,
                        text=True
                    )
                    if version_result.returncode == 0:
                        new_version = version_result.stdout.strip().replace("fucka ", "")
                        if new_version != current_version:
                            print_success(f"Updated: {current_version} → {new_version}")
                        else:
                            print_info(f"Version: {new_version}")
                    else:
                        print_info("Version updated (run 'fucka --version' to check)")
                except:
                    print_info("Version updated (run 'fucka --version' to check)")

                print()
                print_info("Restart any running fucka instances for changes to take effect")

                # Update cache after successful update
                try:
                    checker.save_update_cache({
                        "update_available": False,
                        "current_version": new_version if 'new_version' in locals() else current_version,
                        "latest_version": new_version if 'new_version' in locals() else current_version,
                        "last_check_timestamp": int(__import__('time').time()),
                        "check_interval_hours": 24
                    })
                except:
                    pass

            else:
                print_error("Update failed")
                sys.exit(1)

    except Exception as e:
        print_error(f"Update failed: {e}")
        sys.exit(1)


def _display_update_info(update_info, current_version):
    """Display update information to user"""
    if not update_info:
        print_info(f"Current version: {current_version}")
        print_warning("Could not check for updates")
        return

    if update_info.get("error"):
        print_info(f"Current version: {current_version}")
        print_warning(f"Update check failed: {update_info['error']}")
        return

    channel = update_info.get("channel", "unknown")
    latest_version = update_info.get("latest_version", "unknown")

    print_info(f"Current version: {current_version}")
    print_info(f"Latest version:  {latest_version} ({channel} channel)")

    if update_info.get("update_available"):
        print()
        print_success("Update available!")

        if update_info.get("release_notes"):
            print()
            print("Release Notes:")
            print("─" * 50)
            notes = update_info["release_notes"]
            # Truncate if too long
            if len(notes) > 500:
                notes = notes[:500] + "...\n(see full notes at release URL)"
            print(notes)
            print("─" * 50)

        if update_info.get("release_url"):
            print()
            print_info(f"Details: {update_info['release_url']}")

    else:
        print()
        print_success("You are up to date!")

    if channel == "dev" and update_info.get("latest_commit_sha"):
        print()
        print_info(f"Latest commit: {update_info['latest_commit_sha'][:8]}")


def _check_and_notify_update():
    """Check for updates and display notification banner if available (non-blocking)"""
    try:
        from . import __version__
        from .utils.update_checker import UpdateChecker

        # Quick cache check only (don't hit API on every startup)
        checker = UpdateChecker()
        cached_info = checker.get_cached_update_info()

        if not cached_info:
            return  # No cached info, skip notification

        if checker.is_cache_expired(cached_info):
            return  # Cache expired, don't show stale info

        if not cached_info.get("update_available"):
            return  # No update available

        # Display update notification banner
        latest = cached_info.get("latest_version", "unknown")
        current = __version__
        channel = cached_info.get("channel", "unknown")

        print()
        print("╔" + "═" * 54 + "╗")
        print(f"║  🔔 Update Available: {latest:20} ({channel:6} channel)  ║")
        print(f"║     Current version: {current:20}                    ║")
        print("║     Run 'fucka update' to upgrade                    ║")
        print("╚" + "═" * 54 + "╝")
        print()
    except Exception:
        # Silently fail if update check fails
        pass


def main():
    """Main CLI entry point."""
    # Import version
    from . import __version__

    parser = argparse.ArgumentParser(
        prog='fucka',
        description='Rekordbox MIDI Helper - Because AlphaTheta sucks',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  fucka config                    # Run configuration wizard
  fucka start                     # Start application in background
  fucka start --monitor           # Start with live monitor display
  fucka start --debug             # Start with debug logging
  fucka stop                      # Stop running application
  fucka status                    # Check if running
  fucka monitor                   # Show live monitor display
  fucka update                    # Update to latest version from GitHub
  fucka run                       # Run in foreground (debugging)
  fucka logs                      # Show recent logs
  fucka logs --follow             # Follow logs in real-time
        """
    )

    # Add version flag
    parser.add_argument('--version', '-v', action='version',
                       version=f'fucka {__version__}')

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Config command
    parser_config = subparsers.add_parser('config', help='Run interactive configuration wizard')
    parser_config.add_argument('--config', type=str, default=None,
                               help='Configuration file path (default: ~/.config/fucka/config.yaml)')
    parser_config.set_defaults(func=cmd_config)

    # Start command
    parser_start = subparsers.add_parser('start', help='Start application in background')
    parser_start.add_argument('--config', type=str, default=None,
                              help='Configuration file path (default: ~/.config/fucka/config.yaml)')
    parser_start.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser_start.add_argument('--monitor', '-m', action='store_true',
                              help='Show live monitor display after starting')
    parser_start.set_defaults(func=cmd_start)

    # Stop command
    parser_stop = subparsers.add_parser('stop', help='Stop running application')
    parser_stop.set_defaults(func=cmd_stop)

    # Status command
    parser_status = subparsers.add_parser('status', help='Check application status')
    parser_status.set_defaults(func=cmd_status)

    # Run command (foreground)
    parser_run = subparsers.add_parser('run', help='Run application in foreground')
    parser_run.add_argument('--config', type=str, default=None,
                            help='Configuration file path (default: ~/.config/fucka/config.yaml)')
    parser_run.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser_run.set_defaults(func=cmd_run)

    # Logs command
    parser_logs = subparsers.add_parser('logs', help='Show application logs')
    parser_logs.add_argument('--lines', '-n', type=int, default=50,
                             help='Number of lines to show (default: 50)')
    parser_logs.add_argument('--follow', '-f', action='store_true',
                             help='Follow log file in real-time')
    parser_logs.set_defaults(func=cmd_logs)

    # Monitor command
    parser_monitor = subparsers.add_parser('monitor', help='Show live monitor display')
    parser_monitor.add_argument('--config', type=str, default=None,
                                help='Configuration file path (default: ~/.config/fucka/config.yaml)')
    parser_monitor.set_defaults(func=cmd_monitor)

    # Update command
    parser_update = subparsers.add_parser('update', help='Update fucka to latest version from GitHub')
    parser_update.add_argument('--branch', '-b', type=str, default=None,
                               help='Git branch to install from (default: claude/rekordbox-midi-python-script-FuBNl)')
    parser_update.add_argument('--check', '-c', action='store_true',
                               help='Check for updates without installing')
    parser_update.add_argument('--force', '-f', action='store_true',
                               help='Force reinstall all dependencies (slower)')
    parser_update.add_argument('--dev', '-d', action='store_true',
                               help='Use development channel (latest commits)')
    parser_update.add_argument('--yes', '-y', action='store_true',
                               help='Skip confirmation prompts')
    parser_update.set_defaults(func=cmd_update)

    # Parse arguments
    args = parser.parse_args()

    # Check for updates and show notification (non-blocking, cache-based)
    # Skip for update command itself to avoid redundancy
    if args.command != 'update':
        _check_and_notify_update()

    # Show help if no command specified
    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Execute command
    args.func(args)


if __name__ == '__main__':
    main()
