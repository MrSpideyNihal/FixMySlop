"""
CLI prompts — interactive terminal prompts for model selection and confirmations.
Uses Rich for styled input when available.
"""
from rich.console import Console
from rich.prompt import Prompt, Confirm

console = Console()


def prompt_model_selection(models: list[str], default: str = "") -> str:
    """
    Display available models and let the user pick one.
    Returns the selected model string.
    """
    if not models:
        console.print("[yellow]No models available.[/yellow]")
        return default

    console.print("\n[bold]Available models:[/bold]")
    for i, model in enumerate(models, 1):
        marker = " [green](default)[/green]" if model == default else ""
        console.print(f"  {i}. {model}{marker}")

    choice = Prompt.ask(
        "\nSelect model number or name",
        default=default or models[0],
    )

    # Check if user entered a number
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(models):
            return models[idx]
    except ValueError:
        pass

    # Check if user entered a model name
    if choice in models:
        return choice

    console.print(f"[yellow]Unknown selection '{choice}', using default.[/yellow]")
    return default or models[0]


def prompt_confirm(message: str, default: bool = False) -> bool:
    """Ask the user a yes/no question. Returns True for yes."""
    return Confirm.ask(message, default=default)


def prompt_text(message: str, default: str = "") -> str:
    """Ask the user for a text input. Returns the entered string."""
    return Prompt.ask(message, default=default)


def prompt_backend_url(default: str = "http://localhost:11434/v1") -> str:
    """Ask the user for a backend URL."""
    return Prompt.ask("Backend API URL", default=default)
