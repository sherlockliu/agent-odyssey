"""Full-screen Textual TUI for the Travel Planning Agent – Claude Code style.

Layout
------
  ┌──────────────────────────────────────────────────┐
  │  Transcript / RichLog  (scrollable, 1fr)         │
  │                                                  │
  │  > user message                                  │
  │  ⚙ Thinking... 2.1s                              │
  │  agent response text                             │
  │                                                  │
  ├──────────────────────────────────────────────────┤
  │ ╭──────────────────────────────────────────────╮ │
  │ │ multiline input (auto-height, max 10 lines)  │ │
  │ ╰──────────────────────────────────────────────╯ │
  │   ⚙ DEFAULT  •  Trip: trip_abc123  •  Model: ... │
  └──────────────────────────────────────────────────┘

Key bindings
------------
  Enter        – send message
  Shift+Enter  – insert newline
  Tab          – slash-command completion (when text starts with /)
  Ctrl+Q       – save & quit
  Ctrl+L       – clear transcript
  Ctrl+N       – new session
  Page Up/Down – scroll transcript
  Mouse        – native terminal selection (click-drag to select & copy)
"""
from __future__ import annotations

import queue
import time
import uuid

from textual import events, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import RichLog, Static, TextArea, OptionList
from textual.widgets.option_list import Option

from rich.markdown import Markdown as RichMarkdown
from rich.panel import Panel
from rich.table import Table

import agent as _agent_module
import config as cfg
from config import DEFAULT_MODE, MODES, TRIPS_DIR, LLM_PROVIDER, LLM_MODEL, LLM_PROVIDER_CONFIGS
from llm import create_client
from memory.trip_context import TripContext
from memory.user_profile import UserProfile

# ---------------------------------------------------------------------------
# Slash-command registry (shown in /help and used for Tab completion)
# ---------------------------------------------------------------------------

SLASH_COMMANDS: dict[str, str] = {
    "/help":          "Show available commands",
    "/clear":         "Clear conversation history (keeps trip data)",
    "/clear-trips":   "Delete all saved trips",
    "/trips":         "List all saved trip IDs",
    "/status":        "Show current trip status and itinerary",
    "/context":       "Show context window usage",
    "/profile":        "Show profile, or set a field: /profile set <field> <value>",
    "/mode":          "Set agent mode: passive | default | proactive",
    "/model":         "Set LLM provider/model: /model <provider> <model> or /model ollama qwen3:16b",
    "/new":           "Start a new trip session",
    "/resume":        "Resume a saved trip: /resume <trip-id>",
    "/quick-weekend": "Quick workflow: plan a weekend trip",
    "/export":        "Export current itinerary",
    "/quit":          "Save and exit",
}


# ---------------------------------------------------------------------------
# ComposerInput – TextArea with Enter→send, Shift+Enter→newline
# ---------------------------------------------------------------------------

class ComposerInput(TextArea):
    """Multiline composer that sends on Enter and wraps on Shift+Enter."""

    BINDINGS = [
        # Shift+Enter inserts a newline. Registered as a binding so Textual resolves
        # it before the widget’s key handler — more reliable across terminal emulators.
        Binding("shift+enter", "insert_newline", "New line", show=False),
    ]

    class Submit(Message):
        """Posted when the user presses Enter to submit their input."""

    def action_insert_newline(self) -> None:
        """Insert a literal newline at the cursor (Shift+Enter)."""
        start, end = self.selection
        self._replace_via_keyboard("\n", start, end)

    async def _on_key(self, event: events.Key) -> None:
        if event.key == "enter":
            event.stop()
            event.prevent_default()
            # If suggestions are visible, select the highlighted item instead of submitting.
            try:
                sl = self.app.query_one("#suggestions", OptionList)
                if sl.display:
                    self.app._complete_first_suggestion()  # type: ignore[attr-defined]
                    return
            except Exception:
                pass
            self.post_message(self.Submit())
            # Do NOT call super → no newline inserted.

        elif event.key == "tab":
            text = self.text.rstrip("\n")
            if text.startswith("/") and " " not in text:
                event.stop()
                event.prevent_default()
                self.app._complete_first_suggestion()  # type: ignore[attr-defined]
            else:
                await super()._on_key(event)

        elif event.key == "down":
            # If the suggestion list is visible, move focus there.
            try:
                sl = self.app.query_one("#suggestions", OptionList)
                if sl.display:
                    event.stop()
                    event.prevent_default()
                    sl.focus()
                    return
            except Exception:
                pass
            await super()._on_key(event)

        elif event.key in ("pageup", "pagedown"):
            # TextArea eats pageup/pagedown for cursor movement.
            # Intercept and scroll the transcript instead.
            event.stop()
            event.prevent_default()
            try:
                log = self.app.query_one("#transcript", RichLog)
                if event.key == "pageup":
                    log.scroll_page_up(animate=False)
                else:
                    log.scroll_page_down(animate=False)
            except Exception:
                pass

        else:
            await super()._on_key(event)


# ---------------------------------------------------------------------------
# TravelAgentApp – main full-screen Textual application
# ---------------------------------------------------------------------------

class TravelAgentApp(App):
    """Claude-Code-style full-screen TUI for the Travel Planning Agent."""

    TITLE = "Travel Planning Agent"

    CSS = """
    Screen {
        background: #0d1117;
        color: #e6edf3;
        layout: vertical;
    }

    #transcript {
        height: 1fr;
        padding: 1 2;
        background: #0d1117;
    }

    #composer-area {
        height: auto;
        padding: 0 2 1 2;
        border-top: solid #30363d;
        background: #0d1117;
    }

    #input-row {
        height: auto;
        background: #0d1117;
    }

    #prompt-marker {
        width: 2;
        height: auto;
        padding: 0;
        background: #0d1117;
        content-align: left top;
    }

    #input-area {
        border: none;
        height: auto;
        min-height: 1;
        max-height: 10;
        padding: 0;
        background: #0d1117;
        color: #e6edf3;
    }

    #input-area.thinking {
        background: #161b22;
    }

    #suggestions {
        display: none;
        height: auto;
        max-height: 6;
        border: solid #30363d;
        background: #161b22;
    }

    #metadata-row {
        height: 1;
        color: #8b949e;
        padding: 0 1;
        background: #0d1117;
    }
    """

    BINDINGS = [
        Binding("ctrl+q",    "quit",             "Quit",            show=False),
        Binding("ctrl+l",    "clear_transcript", "Clear",           show=False),
        Binding("ctrl+n",    "new_session",      "New session",     show=False),
        Binding("pageup",    "scroll_up",        "Scroll up",       show=False),
        Binding("pagedown",  "scroll_down",      "Scroll down",     show=False),
    ]

    # Reactive session state – watchers update the metadata row automatically.
    current_mode:  reactive[str] = reactive(DEFAULT_MODE)
    current_model: reactive[str] = reactive(f"{LLM_PROVIDER}/{LLM_MODEL}")
    trip_id:       reactive[str] = reactive("")
    context_count: reactive[int] = reactive(0)
    is_thinking:   reactive[bool] = reactive(False)

    # -----------------------------------------------------------------------
    # Initialisation
    # -----------------------------------------------------------------------

    def __init__(self) -> None:
        super().__init__()
        self._trip: TripContext | None = None
        self._profile: UserProfile | None = None
        self._pending_queue: list[str] = []
        self._steering_queue: queue.Queue[str] | None = None  # h2A: active only during a run
        # Build LLM client from config; updated by /model command.
        self._llm_client = create_client(
            LLM_PROVIDER, LLM_MODEL, **LLM_PROVIDER_CONFIGS.get(LLM_PROVIDER, {})
        )

    def compose(self) -> ComposeResult:
        yield RichLog(id="transcript", highlight=True, markup=True, wrap=True)
        with Vertical(id="composer-area"):
            yield OptionList(id="suggestions")
            with Horizontal(id="input-row"):
                yield Static("[bold green]>[/bold green]", id="prompt-marker")
                yield ComposerInput("", id="input-area", tab_behavior="focus")
            yield Static("", id="metadata-row")

    def on_mount(self) -> None:
        self._profile = UserProfile()
        self._new_trip()
        self._render_welcome()
        self.query_one("#input-area", ComposerInput).focus()
        # Send escape sequences to disable all terminal mouse-tracking modes.
        # Textual enables these in its driver; turning them off restores native
        # click-drag text selection in the terminal emulator.
        import sys
        sys.stdout.write(
            "\x1b[?1000l"   # disable X10 click tracking
            "\x1b[?1002l"   # disable button-event tracking
            "\x1b[?1003l"   # disable all-motion tracking
            "\x1b[?1006l"   # disable SGR extended mouse
        )
        sys.stdout.flush()

    # -----------------------------------------------------------------------
    # Session helpers
    # -----------------------------------------------------------------------

    def _new_trip(self) -> None:
        """Create a fresh TripContext and update reactive state."""
        tid = f"trip_{uuid.uuid4().hex[:8]}"
        self._trip = TripContext(tid)
        self.trip_id = tid
        self.context_count = 0

    def _resume_trip(self, trip_id: str) -> bool:
        """Load an existing saved trip. Returns False if not found."""
        if trip_id not in TripContext.list_trips():
            return False
        self._trip = TripContext(trip_id)
        self.trip_id = trip_id
        self.context_count = len(self._trip.get_conversation_history())
        return True

    # -----------------------------------------------------------------------
    # Reactive watchers → live metadata row
    # -----------------------------------------------------------------------

    def _refresh_metadata(self) -> None:
        if self.is_thinking:
            queued = self._steering_queue.qsize() if self._steering_queue else len(self._pending_queue)
            indicator = f"  [thinking... +{queued} queued]" if queued else "  [thinking...]"
        else:
            indicator = ""
        text = (
            f"  ⚙ {self.current_mode.upper()}"
            f"  •  Trip: {self.trip_id}"
            f"  •  Model: {self.current_model}"
            f"  •  Context: {self.context_count} msgs"
            f"{indicator}"
        )
        try:
            self.query_one("#metadata-row", Static).update(f"[dim]{text}[/dim]")
        except Exception:
            pass  # Tolerate if DOM not yet ready.

    def watch_current_mode(self, _: str)  -> None: self._refresh_metadata()
    def watch_current_model(self, _: str) -> None: self._refresh_metadata()
    def watch_trip_id(self, _: str)       -> None: self._refresh_metadata()
    def watch_context_count(self, _: int) -> None: self._refresh_metadata()

    def watch_is_thinking(self, thinking: bool) -> None:
        self._refresh_metadata()
        try:
            composer = self.query_one("#input-area", ComposerInput)
            prompt = self.query_one("#prompt-marker", Static)
            if thinking:
                composer.add_class("thinking")
                prompt.update("[dim]⚙[/dim]")
            else:
                composer.remove_class("thinking")
                prompt.update("[bold green]>[/bold green]")
                composer.focus()
        except Exception:
            pass

    # Thread-safe setters for use with call_from_thread.
    def _set_is_thinking(self, value: bool) -> None:
        self.is_thinking = value

    def _set_context_count(self, value: int) -> None:
        self.context_count = value

    # -----------------------------------------------------------------------
    # Transcript helpers
    # -----------------------------------------------------------------------

    @property
    def _transcript_log(self) -> RichLog:
        return self.query_one("#transcript", RichLog)

    def _write(self, text: str) -> None:
        """Write a Rich markup string to the transcript."""
        self._transcript_log.write(text)

    def _write_renderable(self, renderable: object) -> None:
        """Write any Rich renderable (Panel, Table, …) to the transcript."""
        self._transcript_log.write(renderable)

    def _write_hint(self, text: str) -> None:
        """Write a dim hint line (used for Tab completion suggestions, etc.)."""
        self._transcript_log.write(f"[dim]{text}[/dim]")

    # -----------------------------------------------------------------------
    # Slash-command suggestion panel
    # -----------------------------------------------------------------------

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Update the suggestion list whenever the composer content changes."""
        if event.text_area.id != "input-area":
            return
        self._update_suggestions(event.text_area.text)

    def _update_suggestions(self, text: str) -> None:
        """Show/hide/populate the OptionList based on current input text."""
        try:
            sl = self.query_one("#suggestions", OptionList)
        except Exception:
            return

        raw = text.rstrip("\n")
        # Show only when typing a slash command with no argument yet.
        if not raw.startswith("/") or " " in raw:
            sl.display = False
            return

        matches = [(cmd, desc) for cmd, desc in SLASH_COMMANDS.items()
                   if cmd.startswith(raw)]
        if not matches:
            sl.display = False
            return

        sl.clear_options()
        for cmd, desc in matches:
            sl.add_option(Option(f"[cyan]{cmd}[/cyan]  [dim]{desc}[/dim]", id=cmd))
        sl.display = True

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Complete the selected command into the input box."""
        if event.option_list.id != "suggestions":
            return
        cmd = str(event.option.id)
        composer = self.query_one("#input-area", ComposerInput)
        composer.load_text(cmd + " ")
        composer.action_cursor_line_end()
        composer.focus()
        event.option_list.display = False

    def _complete_first_suggestion(self) -> None:
        """Tab handler: complete using the first visible suggestion (if any)."""
        try:
            sl = self.query_one("#suggestions", OptionList)
            if not sl.display or sl.option_count == 0:
                return
            # Get the highlighted option (index) or fall back to first.
            idx = sl.highlighted or 0
            opt = sl.get_option_at_index(idx)
            cmd = str(opt.id)
            composer = self.query_one("#input-area", ComposerInput)
            composer.load_text(cmd + " ")
            composer.action_cursor_line_end()
            sl.display = False
        except Exception:
            pass

    def on_key(self, event: events.Key) -> None:
        """App-level key handling for suggestion navigation."""
        if event.key == "escape":
            try:
                sl = self.query_one("#suggestions", OptionList)
                if sl.display:
                    sl.display = False
                    self.query_one("#input-area", ComposerInput).focus()
                    event.stop()
            except Exception:
                pass

        elif event.key == "up":
            # When OptionList is focused and user presses Up at index 0, return to input.
            try:
                sl = self.query_one("#suggestions", OptionList)
                if sl.display and sl.has_focus and (sl.highlighted == 0 or sl.highlighted is None):
                    event.stop()
                    event.prevent_default()
                    sl.display = False
                    self.query_one("#input-area", ComposerInput).focus()
            except Exception:
                pass

    # -----------------------------------------------------------------------
    # Welcome banner
    # -----------------------------------------------------------------------

    def _render_welcome(self) -> None:
        self._write_renderable(Panel.fit(
            f"[bold cyan]Travel Planning Agent[/bold cyan]\n"
            f"[dim]Powered by {self.current_model} · Claude Code Design Patterns[/dim]\n\n"
            "💡 I help you search flights, hotels, and build trip plans.\n"
            "📋 I don't book — I plan.\n\n"
            "[dim]↵ Enter to send  •  ⇧↵ Shift+Enter for newline  •  /help for commands  •  Ctrl+Q to quit[/dim]\n"
            "[dim](If Shift+Enter doesn't wrap, your terminal may not support it — that's a terminal limitation)[/dim]",
            border_style="cyan",
            title="[bold]✈️  Welcome[/bold]",
        ))
        if self._profile and not self._profile.data.get("home_airport"):
            self._write(
                "[yellow]💡 Tip: Set your home airport in .travel-agent/profile.json "
                "for better flight search results.[/yellow]"
            )
        self._write("")

    # -----------------------------------------------------------------------
    # Submit / message dispatch
    # -----------------------------------------------------------------------

    def on_composer_input_submit(self, _: ComposerInput.Submit) -> None:
        """Called when Enter is pressed in the composer."""
        self.action_submit()

    def action_submit(self) -> None:
        """Grab text, echo it to the transcript, or queue it if agent is busy."""
        composer = self.query_one("#input-area", ComposerInput)
        text = composer.text.strip()
        composer.load_text("")  # Clear the input box.

        if not text:
            return

        if self.is_thinking:
            # h2A: if agent is mid-loop, inject directly into steering queue so the
            # model sees it at the next decision point (before the next model call).
            if self._steering_queue is not None:
                self._steering_queue.put(text)
                position = self._steering_queue.qsize()
                self._write_hint(f"⏳ Queued [{position}] (will steer agent): {text}")
            else:
                # Agent turn finishing up — fall back to post-turn queue.
                self._pending_queue.append(text)
                position = len(self._pending_queue)
                self._write_hint(f"⏳ Queued [{position}]: {text}")
            self._refresh_metadata()
            return

        # Echo the user message to transcript.
        self._write(f"[bold cyan]>[/bold cyan] {text}")
        self._write("")

        if text.startswith("/"):
            self._handle_slash_command(text)
        else:
            self._run_agent(text)

    # -----------------------------------------------------------------------
    # Agent worker (runs in a background thread)
    # -----------------------------------------------------------------------

    @work(thread=True, exclusive=True)
    def _run_agent(self, user_input: str) -> None:
        """Run the ReAct agent loop in a background thread."""
        self.call_from_thread(self._set_is_thinking, True)

        # Create a fresh steering queue for this turn (h2A pattern).
        self._steering_queue = queue.Queue()

        def print_fn(text: str) -> None:
            # Rich-markup lines start with '['; plain text is LLM output → render as Markdown.
            if text and not text.lstrip().startswith("["):
                self.call_from_thread(self._write_renderable, RichMarkdown(text))
            else:
                self.call_from_thread(self._write, text)

        def thinking_fn(status: str, elapsed: float = 0, stats: dict | None = None) -> None:
            if status == "loop_start":
                if stats and stats.get("iteration", 1) > 1:
                    # Only show from loop 2+ so the first call is quiet
                    self.call_from_thread(
                        self._write_hint,
                        f"↩  Loop {stats['iteration']} — continuing...",
                    )

            elif status == "context_loaded":
                if stats:
                    parts: list[str] = []
                    if stats.get("skills"):
                        parts.append(f"📚 Skills: {', '.join(stats['skills'])}")
                    if stats.get("command"):
                        parts.append(f"⚡ Command: {stats['command']}")
                    if parts:
                        self.call_from_thread(self._write_hint, " • ".join(parts))

            elif status == "compression":
                if stats:
                    if stats.get("status") == "compressing":
                        self.call_from_thread(
                            self._write_hint,
                            f"🗜  Compressing context: {stats['old']} messages → summarizing...",
                        )
                    elif stats.get("status") == "compressed":
                        self.call_from_thread(
                            self._write_hint,
                            f"✓ Compressed: {stats['old']} → {stats['new']} messages",
                        )

            elif status == "steered":
                # A mid-loop user message was injected — echo it to transcript.
                if stats and stats.get("message"):
                    self.call_from_thread(
                        self._write,
                        f"[bold cyan]>[/bold cyan] {stats['message']}",
                    )
                    self.call_from_thread(self._write, "")

            elif status == "thinking":
                self.call_from_thread(self._write_hint, "⚙  Asking model...")

            elif status == "profile_update":
                if stats:
                    action = stats.get("action", "")
                    args = stats.get("args", {})
                    field = args.get("field", "?")
                    value = args.get("value", "?")
                    source = args.get("source", "explicit")
                    if action == "update_profile" and source == "inferred":
                        self.call_from_thread(
                            self._write_hint,
                            f"[yellow]👤 Profile (staged for confirm):[/yellow] {field} = {value!r}",
                        )
                    elif action == "update_profile":
                        self.call_from_thread(
                            self._write_hint,
                            f"[green]👤 Profile saved:[/green] {field} = {value!r}",
                        )
                    elif action == "confirm_profile_update":
                        self.call_from_thread(
                            self._write_hint,
                            f"[green]👤 Profile confirmed:[/green] {field}",
                        )
                    elif action == "discard_profile_update":
                        self.call_from_thread(
                            self._write_hint,
                            f"[dim]👤 Profile update discarded:[/dim] {field}",
                        )

            elif status == "todo_updated":
                if stats and stats.get("items"):
                    items = stats["items"]
                    symbols = {"pending": "[ ]", "in_progress": "[→]", "done": "[✓]"}
                    parts = []
                    for item in items:
                        sym = symbols.get(item["status"], "[ ]")
                        task = item["task"]
                        if item["status"] == "done":
                            parts.append(f"[dim]{sym} {task}[/dim]")
                        elif item["status"] == "in_progress":
                            parts.append(f"[cyan]{sym} {task}[/cyan]")
                        else:
                            parts.append(f"{sym} {task}")
                    summary = "  ".join(parts)
                    self.call_from_thread(
                        self._write_hint,
                        f"📋 TODO: {summary}",
                    )

            elif status == "done":
                time_str = (
                    f"{int(elapsed // 60)}m {int(elapsed % 60)}s"
                    if elapsed >= 60
                    else f"{elapsed:.1f}s"
                )
                if stats:
                    parts = []
                    if stats.get("prompt_tokens"):
                        parts.append(f"{stats['prompt_tokens']} prompt")
                    if stats.get("completion_tokens"):
                        parts.append(f"{stats['completion_tokens']} completion")
                    if stats.get("tokens_per_sec"):
                        parts.append(f"{stats['tokens_per_sec']:.1f} tok/s")
                    # Show cache hits when Anthropic prompt caching is active
                    cache_read = stats.get("cache_read_tokens", 0)
                    cache_write = stats.get("cache_creation_tokens", 0)
                    if cache_read:
                        parts.append(f"[green]{cache_read} cached[/green]")
                    if cache_write:
                        parts.append(f"[yellow]{cache_write} cache-write[/yellow]")
                    suffix = f" • {' • '.join(parts)}" if parts else ""
                    self.call_from_thread(self._write_hint, f"✻ Cogitated for {time_str}{suffix}")
                else:
                    self.call_from_thread(self._write_hint, f"✻ Cogitated for {time_str}")
                self.call_from_thread(self._write, "")

        try:
            run_agent = _agent_module.run_agent
            run_agent(
                user_input=user_input,
                trip_context=self._trip,
                mode=self.current_mode,
                print_fn=print_fn,
                thinking_fn=thinking_fn,
                steering_queue=self._steering_queue,
                llm_client=self._llm_client,
                user_profile=self._profile,
            )
        except Exception as exc:
            self.call_from_thread(
                self._write_renderable,
                Panel(
                    f"[red]Error: {exc}[/red]\n\n"
                    "[dim]Check your LLM provider config. For Ollama: ollama serve[/dim]",
                    title="[bold red]⚠  Error[/bold red]",
                    border_style="red",
                ),
            )
        finally:
            self._steering_queue = None  # Discard; any late pushes fall to _pending_queue.
            # Reload profile in case the agent updated it during the turn.
            from memory.user_profile import UserProfile
            self._profile = UserProfile()
            assert self._trip is not None
            count = len(self._trip.get_conversation_history())
            self.call_from_thread(self._set_context_count, count)
            self.call_from_thread(self._set_is_thinking, False)
            self.call_from_thread(self._write, "")
            self.call_from_thread(self._drain_pending_queue)

    def _drain_pending_queue(self) -> None:
        """Process the next pending queued message, if any."""
        if not self._pending_queue:
            return
        text = self._pending_queue.pop(0)
        self._write(f"[bold cyan]>[/bold cyan] {text}")
        if self._pending_queue:
            self._write_hint(f"[dim]({len(self._pending_queue)} more in queue)[/dim]")
        self._write("")
        if text.startswith("/"):
            self._handle_slash_command(text)
        else:
            self._run_agent(text)

    # -----------------------------------------------------------------------
    # Slash-command dispatcher
    # -----------------------------------------------------------------------

    def _handle_slash_command(self, text: str) -> None:
        """Dispatch slash commands. Unrecognised commands fall through to the agent."""
        parts = text.strip().split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        dispatch = {
            "/help":          lambda: self._cmd_help(),
            "/clear":         lambda: self._cmd_clear(),
            "/clear-trips":   lambda: self._cmd_clear_trips(),
            "/trips":         lambda: self._cmd_trips(),
            "/status":        lambda: self._cmd_status(),
            "/context":       lambda: self._cmd_context(),
            "/profile":       lambda: self._cmd_profile(arg),
            "/mode":          lambda: self._cmd_mode(arg),
            "/model":         lambda: self._cmd_model(arg),
            "/new":           lambda: self._cmd_new(),
            "/resume":        lambda: self._cmd_resume(arg),
            "/quit":          lambda: self.action_quit(),
            "/exit":          lambda: self.action_quit(),
            # These are forwarded to the agent (template injection happens in agent.py).
            "/quick-weekend": lambda: self._run_agent(text),
            "/export":        lambda: self._run_agent(text),
            # /profile with no args → agent Q&A (profile.md template injected in agent.py).
            # /profile set <field> <value> → TUI handles directly (no round-trip to model).
            "/profile":       lambda: self._run_agent(text) if not arg else self._cmd_profile(arg),
        }

        handler = dispatch.get(cmd)
        if handler:
            handler()
        else:
            self._write(
                f"[yellow]Unknown command:[/yellow] {cmd}\n"
                "[dim]Type /help to see available commands.[/dim]"
            )
            self._write("")

    # -----------------------------------------------------------------------
    # Slash-command implementations
    # -----------------------------------------------------------------------

    def _cmd_help(self) -> None:
        t = Table(show_header=True, header_style="bold cyan", border_style="dim")
        t.add_column("Command",     style="cyan", width=18)
        t.add_column("Description", width=55)
        for cmd, desc in SLASH_COMMANDS.items():
            t.add_row(cmd, desc)
        self._write_renderable(Panel(t, title="[bold]📚 Commands[/bold]", border_style="cyan"))
        self._write("")

    def _cmd_clear(self) -> None:
        assert self._trip is not None
        self._trip.data["conversation_history"] = []
        self._trip.save()
        self.context_count = 0
        self._transcript_log.clear()
        self._write("[green]✓ Conversation history cleared. Trip data preserved.[/green]")
        self._write("")

    def _cmd_clear_trips(self) -> None:
        if TRIPS_DIR.exists():
            import shutil as _sh
            _sh.rmtree(TRIPS_DIR)
            self._write("[green]✓ All saved trips deleted.[/green]")
        else:
            self._write("[dim]No saved trips to delete.[/dim]")
        self._write("")

    def _cmd_trips(self) -> None:
        trips = TripContext.list_trips()
        if trips:
            self._write_renderable(Panel(
                "\n".join(f"  • {t}" for t in trips),
                title="[bold]📁 Saved Trips[/bold]",
                border_style="cyan",
            ))
        else:
            self._write("[dim]No saved trips.[/dim]")
        self._write("")

    def _cmd_status(self) -> None:
        assert self._trip is not None
        trip   = self._trip
        dest   = trip.data.get("destination") or "[dim]Not set[/dim]"
        dates  = trip.data.get("dates") or {}
        budget = trip.data.get("budget", {}).get("total", 0)
        items  = trip.data.get("itinerary", [])
        spent  = sum(i.get("est_cost", 0) for i in items)

        t = Table(show_header=False, box=None, padding=(0, 2))
        t.add_column("Key",   style="bold cyan", width=20)
        t.add_column("Value")
        t.add_row("Trip ID",          trip.trip_id)
        t.add_row("Mode",             f"[bold]{self.current_mode.upper()}[/bold]")
        t.add_row("Model",            self.current_model)
        t.add_row("Destination",      dest)
        t.add_row("Dates",            str(dates) if dates else "[dim]Not set[/dim]")
        t.add_row("Budget",           f"${budget:,.0f}" if budget else "[dim]Not set[/dim]")
        t.add_row("Estimated Spend",  f"${spent:,.0f}")
        t.add_row("Remaining",        f"${budget - spent:,.0f}" if budget else "[dim]N/A[/dim]")
        t.add_row("Itinerary Items",  str(len(items)))
        t.add_row("Context Messages", str(self.context_count))
        self._write_renderable(Panel(t, title="[bold]📊 Trip Status[/bold]", border_style="cyan"))

        if items:
            self._write("[bold]📋 Current Itinerary:[/bold]")
            for i, item in enumerate(items, 1):
                name = item.get("name", item.get("id", "Unknown"))
                cost = item.get("est_cost", 0)
                self._write(f"  {i}. {name} [dim](${cost:,.0f})[/dim]")
        self._write("")

    def _cmd_context(self) -> None:
        assert self._trip is not None
        history   = self._trip.get_conversation_history()
        user_msgs = sum(1 for m in history if m.get("role") == "user")
        asst_msgs = sum(1 for m in history if m.get("role") == "assistant")
        tool_msgs = sum(1 for m in history if m.get("role") == "tool")
        est_tok   = sum(len(str(m.get("content", ""))) for m in history) // 4

        t = Table(show_header=False, box=None, padding=(0, 2))
        t.add_column("Metric", style="bold cyan", width=25)
        t.add_column("Value")
        t.add_row("Total Messages",     str(len(history)))
        t.add_row("User Messages",      str(user_msgs))
        t.add_row("Assistant Messages", str(asst_msgs))
        t.add_row("Tool Calls",         str(tool_msgs))
        t.add_row("Estimated Tokens",   f"~{est_tok:,}")
        self._write_renderable(Panel(t, title="[bold]💾 Context Window[/bold]", border_style="cyan"))
        self._write("")

    # Fields that hold a plain list (comma-separated input).
    _PROFILE_LIST_FIELDS = {
        "airlines":  "preferred_airlines",
        "hotels":    "preferred_hotel_chains",
        "interests": "interests",
        "avoid":     "avoid",
    }
    # Fields that hold a plain string.
    _PROFILE_STR_FIELDS = {
        "name":    "name",
        "airport": "home_airport",
        "seat":    "seat_preference",
    }
    # Fields that live inside budget_defaults.
    _PROFILE_BUDGET_FIELDS = {
        "flight_budget": "flight_max_usd",
        "hotel_budget":  "hotel_max_per_night_usd",
    }

    def _cmd_profile(self, arg: str = "") -> None:
        """Show profile or set a field.

        Usage:
          /profile                     – show all fields
          /profile set name Alice
          /profile set airport SFO
          /profile set seat window|aisle|middle
          /profile set airlines United,Delta
          /profile set hotels Marriott,Hilton
          /profile set interests hiking,food,culture
          /profile set avoid crowds,long-haul
          /profile set flight_budget 1200
          /profile set hotel_budget 350
        """
        # ── /profile set <field> <value> ──────────────────────────────────
        if arg.lower().startswith("set "):
            rest   = arg[4:].strip()          # everything after "set "
            parts  = rest.split(maxsplit=1)
            if len(parts) < 2:
                self._write("[yellow]Usage: /profile set <field> <value>[/yellow]")
                self._write("[dim]Fields: name · airport · seat · airlines · hotels · interests · avoid · flight_budget · hotel_budget[/dim]")
                self._write("")
                return

            field, value = parts[0].lower(), parts[1].strip()

            if not self._profile:
                self._write("[red]Profile not loaded.[/red]")
                self._write("")
                return

            if field in self._PROFILE_STR_FIELDS:
                key = self._PROFILE_STR_FIELDS[field]
                self._profile.data[key] = value
                self._profile.save()
                self._write(f"[green]✓ {key.replace('_', ' ').title()} set to: {value}[/green]")

            elif field in self._PROFILE_LIST_FIELDS:
                key  = self._PROFILE_LIST_FIELDS[field]
                items = [v.strip() for v in value.split(",") if v.strip()]
                self._profile.data[key] = items
                self._profile.save()
                self._write(f"[green]✓ {key.replace('_', ' ').title()} set to: {', '.join(items)}[/green]")

            elif field in self._PROFILE_BUDGET_FIELDS:
                key = self._PROFILE_BUDGET_FIELDS[field]
                try:
                    amount = int(value.replace(",", "").replace("$", ""))
                    self._profile.data.setdefault("budget_defaults", {})[key] = amount
                    self._profile.save()
                    self._write(f"[green]✓ {key.replace('_', ' ').title()} set to: ${amount:,}[/green]")
                except ValueError:
                    self._write(f"[red]Invalid amount: {value}  (use a number, e.g. 1200)[/red]")

            else:
                self._write(f"[yellow]Unknown field: {field}[/yellow]")
                self._write("[dim]Fields: name · airport · seat · airlines · hotels · interests · avoid · flight_budget · hotel_budget[/dim]")

            self._write("")
            return

        # ── /profile  (show) ──────────────────────────────────────────────
        p      = self._profile.data if self._profile else {}
        budget = p.get("budget_defaults", {})
        loyalty = p.get("loyalty_programs", {})

        t = Table(show_header=False, box=None, padding=(0, 2))
        t.add_column("Field",  style="bold cyan", width=26)
        t.add_column("Value")

        def _row(label: str, value: object) -> None:
            if isinstance(value, list):
                t.add_row(label, ", ".join(str(v) for v in value) if value else "[dim]Not set[/dim]")
            elif isinstance(value, dict):
                t.add_row(label, ", ".join(f"{k}: {v}" for k, v in value.items()) if value else "[dim]Not set[/dim]")
            else:
                t.add_row(label, str(value) if value else "[dim]Not set[/dim]")

        _row("Name",                  p.get("name"))
        _row("Home Airport",          p.get("home_airport"))
        _row("Seat Preference",       p.get("seat_preference"))
        _row("Preferred Airlines",    p.get("preferred_airlines", []))
        _row("Preferred Hotels",      p.get("preferred_hotel_chains", []))
        _row("Loyalty Programs",      loyalty)
        _row("Flight Budget Max",     f"${budget.get('flight_max_usd', 0):,}" if budget else None)
        _row("Hotel Budget Max/Night", f"${budget.get('hotel_max_per_night_usd', 0):,}" if budget else None)
        _row("Interests",             p.get("interests", []))
        _row("Avoid",                 p.get("avoid", []))
        _row("Past Trips",            len(p.get("past_trips", [])))

        from config import PROFILE_PATH
        self._write_renderable(Panel(
            t,
            title="[bold]👤 Traveller Profile[/bold]",
            border_style="cyan",
            subtitle=f"[dim]{PROFILE_PATH}[/dim]",
        ))
        self._write("[dim]Use /profile set <field> <value> to update a field.[/dim]")
        self._write("[dim]Fields: name · airport · seat · airlines · hotels · interests · avoid · flight_budget · hotel_budget[/dim]")
        self._write("")

    def _cmd_mode(self, arg: str) -> None:
        if arg in MODES:
            self.current_mode = arg
            self._write(f"[green]✓ Mode set to: {arg}[/green]")
            self._write(f"[dim]{MODES[arg]}[/dim]")
        else:
            self._write(f"[yellow]Available modes: {', '.join(MODES.keys())}[/yellow]")
            self._write(f"[dim]Current mode: {self.current_mode}[/dim]")
        self._write("")

    def _cmd_model(self, arg: str) -> None:
        """Switch LLM provider and/or model at runtime.

        /model qwen3:16b                  → swap model, keep ollama provider
        /model anthropic claude-opus-4-5  → swap provider and model
        /model ollama qwen3:16b           → explicit provider + model
        """
        if not arg:
            self._write(f"[dim]Current model: {self.current_model}[/dim]")
            self._write(
                "[dim]Usage: /model <model>  or  /model <provider> <model>\n"
                "Providers: ollama · anthropic · openai · groq · together · gemini[/dim]"
            )
            self._write("")
            return

        parts = arg.strip().split(maxsplit=1)
        known_providers = {"ollama", "anthropic", "openai", "groq", "together", "gemini"}

        if len(parts) == 2 and parts[0].lower() in known_providers:
            provider, model = parts[0].lower(), parts[1]
        elif len(parts) == 1:
            # Single-word: if it looks like an Ollama model (contains ':'), use ollama.
            provider = "ollama" if ":" in parts[0] else self._llm_client.provider_name
            model = parts[0]
        else:
            self._write(f"[yellow]Usage: /model <model>  or  /model <provider> <model>[/yellow]")
            self._write("")
            return

        # Check API key requirements before switching.
        _required_keys = {
            "anthropic": "ANTHROPIC_API_KEY",
            "openai":    "OPENAI_API_KEY",
            "groq":      "GROQ_API_KEY",
            "together":  "TOGETHER_API_KEY",
            "gemini":    "GEMINI_API_KEY",
        }
        if provider in _required_keys:
            cfg_key = LLM_PROVIDER_CONFIGS.get(provider, {}).get("api_key")
            if not cfg_key:
                env_var = _required_keys[provider]
                self._write(
                    f"[yellow]⚠ {env_var} is not set.[/yellow]\n"
                    f"[dim]Set it with: export {env_var}=your-key-here[/dim]"
                )
                self._write("")
                return

        try:
            provider_cfg = LLM_PROVIDER_CONFIGS.get(provider, {})
            new_client = create_client(provider, model, **provider_cfg)
            self._llm_client = new_client
            self.current_model = new_client.display_name()
            self._write(f"[green]✓ Switched to {self.current_model}[/green]")
        except (ValueError, ImportError) as exc:
            self._write(f"[red]Failed to switch model: {exc}[/red]")
        self._write("")

    def _cmd_new(self) -> None:
        if self._trip:
            self._trip.save()
        self._new_trip()
        self._transcript_log.clear()
        self._render_welcome()
        self._write(f"[green]✓ New session started: {self.trip_id}[/green]")
        self._write("")

    def _cmd_resume(self, arg: str) -> None:
        if not arg:
            self._cmd_trips()
            self._write("[dim]Usage: /resume <trip-id>[/dim]")
            self._write("")
            return
        if self._resume_trip(arg):
            assert self._trip is not None
            dest       = self._trip.data.get("destination") or "Not set"
            hist_count = len(self._trip.get_conversation_history())
            self._write(f"[green]✓ Resumed trip: {arg}[/green]")
            self._write(f"[dim]  Destination: {dest}  •  {hist_count} messages[/dim]")
        else:
            self._write(f"[red]Trip not found: {arg}[/red]")
            self._write("[dim]Use /trips to list available trips.[/dim]")
        self._write("")

    # -----------------------------------------------------------------------
    # Action bindings
    # -----------------------------------------------------------------------

    def action_quit(self) -> None:
        if self._trip:
            self._trip.save()
        self.exit()

    def action_clear_transcript(self) -> None:
        self._transcript_log.clear()
        self._write("[dim]Transcript cleared.[/dim]")
        self._write("")

    def action_new_session(self) -> None:
        self._cmd_new()

    def action_scroll_up(self) -> None:
        self._transcript_log.scroll_page_up(animate=True)

    def action_scroll_down(self) -> None:
        self._transcript_log.scroll_page_down(animate=True)


# ---------------------------------------------------------------------------
# Entry point (also callable as python tui.py)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    TravelAgentApp().run()
