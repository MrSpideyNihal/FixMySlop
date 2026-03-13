"""
FixMySlop entry point.
- No args → launch GUI
- Any CLI args → hand off to CLI
- --version / --help → CLI handles it
"""
import sys


def main():
    """Launch GUI if no args given, otherwise run CLI."""
    # If any meaningful CLI args are present, use CLI
    cli_commands = {"scan", "models", "version", "--help", "-h", "--version"}
    if len(sys.argv) > 1 and any(
        arg in cli_commands or arg.startswith("-") for arg in sys.argv[1:]
    ):
        from cli.cli_app import app
        app()
    else:
        # Launch GUI
        try:
            from ui.app import launch
            launch()
        except ImportError:
            print("PyQt5 not installed. Use CLI mode: fixmyslop scan <path>")
            sys.exit(1)


if __name__ == "__main__":
    main()
