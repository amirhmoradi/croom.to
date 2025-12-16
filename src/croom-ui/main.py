#!/usr/bin/env python3
"""
Croom Touch UI - Main entry point.

Touch-based room management interface for Raspberry Pi.
"""

import sys
import os
import argparse
import logging

# Add parent directory to path for croom module access
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    """Main entry point for Croom Touch UI."""
    parser = argparse.ArgumentParser(description="Croom Touch UI")
    parser.add_argument(
        "-c", "--config",
        help="Path to configuration file",
        default=None
    )
    parser.add_argument(
        "-v", "--verbose",
        help="Enable verbose logging",
        action="store_true"
    )
    parser.add_argument(
        "--debug",
        help="Enable debug mode",
        action="store_true"
    )
    parser.add_argument(
        "--fullscreen",
        help="Start in fullscreen mode",
        action="store_true",
        default=True
    )
    parser.add_argument(
        "--windowed",
        help="Start in windowed mode",
        action="store_true"
    )

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.debug else (logging.INFO if args.verbose else logging.WARNING)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Import Qt after parsing args to avoid slow startup on --help
    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QCoreApplication
        from croom_ui.app import CroomUI
    except ImportError as e:
        print(f"Error: PySide6 not installed. Run: pip install PySide6")
        print(f"Details: {e}")
        sys.exit(1)

    # Set application info
    QCoreApplication.setOrganizationName("Croom")
    QCoreApplication.setOrganizationDomain("croom.local")
    QCoreApplication.setApplicationName("Croom Room Controller")

    # Create application
    app = QApplication(sys.argv)

    # Create and show main window
    fullscreen = args.fullscreen and not args.windowed
    ui = CroomUI(
        config_path=args.config,
        fullscreen=fullscreen,
        debug=args.debug
    )
    ui.show()

    # Run event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
