"""Package entry point for the fixmyslop console script."""


def main():
    """Forward to the root main.py entrypoint."""
    from main import main as root_main

    root_main()


if __name__ == "__main__":
    main()
