"""Quick visual test of the composer UI."""

import shutil
from rich.console import Console

console = Console()


def get_terminal_width() -> int:
    """Get current terminal width, default to 80."""
    try:
        return shutil.get_terminal_size().columns
    except:
        return 80


def render_composer_border(position: str = "top") -> str:
    """Render top or bottom border for the composer box."""
    width = get_terminal_width()
    box_width = min(width - 4, 90)
    
    if position == "top":
        return f"╭{'─' * (box_width - 2)}╮"
    else:
        return f"╰{'─' * (box_width - 2)}╯"


def demo():
    """Demonstrate the composer UI - Claude Code style."""
    console.print("\n[bold cyan]Composer UI Demo - Claude Code Style[/bold cyan]\n")
    
    # Single-line example
    console.print("[bold]1. Single-line input:[/bold]")
    console.print(f"[cyan]{render_composer_border('top')}[/cyan]")
    console.print("[cyan]│[/cyan] /status")
    console.print(f"[cyan]{render_composer_border('bottom')}[/cyan]")
    console.print("[dim]  ⚙ DEFAULT  •  Trip: trip_abc123  •  Model: qwen3:8b  •  Context: 0 msgs[/dim]")
    
    console.print("\n")
    
    # Multi-line example
    console.print("[bold]2. Multi-line input (compact):[/bold]")
    console.print(f"[cyan]{render_composer_border('top')}[/cyan]")
    console.print("[cyan]│[/cyan] Plan a 3-day weekend trip to Portland")
    console.print("[cyan]│[/cyan] for 2 people, budget $1500 total.")
    console.print(f"[cyan]{render_composer_border('bottom')}[/cyan]")
    console.print("[dim]  ⚙ DEFAULT  •  Trip: trip_abc123  •  Model: qwen3:8b  •  Context: 3 msgs[/dim]")
    
    console.print("\n")
    
    # Long message with wrapping
    console.print("[bold]3. Long message with natural wrapping:[/bold]")
    console.print(f"[cyan]{render_composer_border('top')}[/cyan]")
    console.print("[cyan]│[/cyan] I'm planning a trip to Japan in April and need help with the itinerary.")
    console.print("[cyan]│[/cyan] I want to visit Tokyo, Kyoto, and Osaka. Budget is around $3000 per person")
    console.print("[cyan]│[/cyan] excluding flights. Interested in temples, food, and nature.")
    console.print(f"[cyan]{render_composer_border('bottom')}[/cyan]")
    console.print("[dim]  ⚙ PROACTIVE  •  Trip: trip_def456  •  Model: qwen3:8b  •  Context: 12 msgs[/dim]")
    
    console.print("\n[bold green]✓ Compact composer - Claude Code style![/bold green]")
    console.print("[dim]Notice: Metadata printed as regular line below border, not as full-width toolbar[/dim]\n")
    
    # Width info
    width = get_terminal_width()
    box_width = min(width - 4, 90)
    console.print(f"[dim]Terminal width: {width} chars  •  Composer width: {box_width} chars[/dim]\n")


if __name__ == "__main__":
    demo()
