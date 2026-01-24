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
    """Run the configuration menu."""
    from .configure import ConfigMenu
    from .utils.config_path import ensure_config_exists

    print_info("Starting configuration menu...")
    print()

    # Use ~/.config/fucka/config.yaml (or custom path if provided)
    if hasattr(args, 'config') and args.config:
        config_path = args.config
    else:
        config_path = str(ensure_config_exists())

    menu = ConfigMenu(config_path)

    try:
        menu.run()
    except KeyboardInterrupt:
        print("\n")
        print_warning("Configuration menu cancelled")
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
            print_info(f"Use 'fucka status' to check status")
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

    config_path = args.config

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
  fucka start --debug             # Start with debug logging
  fucka stop                      # Stop running application
  fucka status                    # Check if running
  fucka run                       # Run in foreground
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
    parser_config.add_argument('--config', type=str, default='config/config.yaml',
                               help='Configuration file path')
    parser_config.set_defaults(func=cmd_config)

    # Start command
    parser_start = subparsers.add_parser('start', help='Start application in background')
    parser_start.add_argument('--config', type=str, default='config/config.yaml',
                              help='Configuration file path')
    parser_start.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser_start.set_defaults(func=cmd_start)

    # Stop command
    parser_stop = subparsers.add_parser('stop', help='Stop running application')
    parser_stop.set_defaults(func=cmd_stop)

    # Status command
    parser_status = subparsers.add_parser('status', help='Check application status')
    parser_status.set_defaults(func=cmd_status)

    # Run command (foreground)
    parser_run = subparsers.add_parser('run', help='Run application in foreground')
    parser_run.add_argument('--config', type=str, default='config/config.yaml',
                            help='Configuration file path')
    parser_run.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser_run.set_defaults(func=cmd_run)

    # Logs command
    parser_logs = subparsers.add_parser('logs', help='Show application logs')
    parser_logs.add_argument('--lines', '-n', type=int, default=50,
                             help='Number of lines to show (default: 50)')
    parser_logs.add_argument('--follow', '-f', action='store_true',
                             help='Follow log file in real-time')
    parser_logs.set_defaults(func=cmd_logs)

    # Parse arguments
    args = parser.parse_args()

    # Show help if no command specified
    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Execute command
    args.func(args)


if __name__ == '__main__':
    main()
