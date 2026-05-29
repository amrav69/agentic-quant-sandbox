"""
tui.py — Agentic Quant Sandbox TUI
Bloomberg Terminal × Institutional Quant Desk × AI Research Lab

Architecture:
  - QuantApp          : Root Textual application
  - HeaderBar         : Live clock + backend status
  - SidebarNav        : View switcher (Dashboard / Analyze / History)
  - DashboardView     : Agent status cards + recent feed + system info
  - AnalyzeView       : Ticker input + sequential agent pipeline display
  - HistoryView       : DataTable of past analyses
  - BackendClient     : Async httpx wrapper around FastAPI endpoints
  - HistoryStore      : In-memory run history
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx
from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, ScrollableContainer, Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Input,
    LoadingIndicator,
    RichLog,
    Static,
)

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

BASE_URL = "http://127.0.0.1:8000"
REQUEST_TIMEOUT = 90.0  # seconds; LLM calls are slow

APP_CSS = """
/* ── Global ──────────────────────────────────────────────── */
Screen {
    background: #050810;
    color: #c8d8e8;
}

/* ── Header ──────────────────────────────────────────────── */
#header-bar {
    height: 3;
    background: #080f1a;
    border-bottom: solid #0d2035;
    layout: horizontal;
    align: left middle;
    padding: 0 2;
}

#app-title {
    color: #00d4ff;
    text-style: bold;
    width: auto;
    padding: 0 2 0 0;
}

#header-sep-1, #header-sep-2 {
    color: #1a3a5c;
    width: auto;
}

#header-clock {
    color: #7a9ab8;
    width: auto;
    padding: 0 2;
}

#backend-status {
    width: auto;
    padding: 0 1;
}

/* ── Layout shell ────────────────────────────────────────── */
#app-body {
    layout: horizontal;
    height: 1fr;
}

/* ── Sidebar ─────────────────────────────────────────────── */
#sidebar {
    width: 18;
    background: #060d18;
    border-right: solid #0d2035;
    padding: 1 0;
}

#sidebar-title {
    color: #1a5070;
    text-style: bold;
    padding: 0 2 1 2;
    border-bottom: solid #0d2035;
    width: 100%;
}

.nav-item {
    height: 3;
    padding: 0 2;
    color: #4a6a8a;
    width: 100%;
    background: transparent;
    border: none;
    text-align: left;
    content-align: left middle;
}

.nav-item:hover {
    color: #00d4ff;
    background: #091520;
}

.nav-item.active {
    color: #00d4ff;
    background: #091a2a;
    border-left: solid #00d4ff;
    text-style: bold;
}

/* ── Main area ───────────────────────────────────────────── */
#main-content {
    width: 1fr;
    height: 1fr;
}

/* ── Views ───────────────────────────────────────────────── */
.view {
    height: 1fr;
    padding: 1 2;
}

/* ── Section headers ─────────────────────────────────────── */
.section-label {
    color: #1a5070;
    text-style: bold;
    padding: 0 0 1 0;
}

/* ── Agent cards ─────────────────────────────────────────── */
#agent-cards {
    height: 7;
    layout: horizontal;
    margin: 0 0 1 0;
}

.agent-card {
    width: 1fr;
    height: 100%;
    border: solid #0d2035;
    background: #060d18;
    padding: 1 2;
    margin: 0 1 0 0;
}

.agent-card-name {
    color: #00d4ff;
    text-style: bold;
}

.agent-card-status {
    color: #4a6a8a;
    padding: 0 0 0 0;
}

.agent-card-desc {
    color: #2a4a6a;
}

.card-active .agent-card-status {
    color: #00ff99;
}

.card-idle .agent-card-status {
    color: #4a6a8a;
}

.card-error .agent-card-status {
    color: #ff4466;
}

/* ── Dashboard panels ────────────────────────────────────── */
#dash-bottom {
    layout: horizontal;
    height: 1fr;
}

#recent-feed {
    width: 1fr;
    border: solid #0d2035;
    background: #060d18;
    margin: 0 1 0 0;
    padding: 1;
}

#system-status {
    width: 30;
    border: solid #0d2035;
    background: #060d18;
    padding: 1;
}

.status-row {
    color: #4a6a8a;
    height: 1;
}

.status-key {
    color: #2a6080;
}

.status-ok {
    color: #00ff99;
}

.status-err {
    color: #ff4466;
}

/* ── Analyze view ────────────────────────────────────────── */
#analyze-input-bar {
    height: 5;
    layout: horizontal;
    align: left middle;
    border: solid #0d2035;
    background: #060d18;
    padding: 1 2;
    margin: 0 0 1 0;
}

#ticker-input {
    width: 30;
    background: #080f1a;
    border: solid #1a3a5c;
    color: #00d4ff;
    padding: 0 1;
    margin: 0 2 0 0;
}

#ticker-input:focus {
    border: solid #00d4ff;
}

#run-btn {
    width: auto;
    background: #002244;
    color: #00d4ff;
    border: solid #0d4070;
    padding: 0 3;
    text-style: bold;
}

#run-btn:hover {
    background: #003366;
    border: solid #00d4ff;
}

#run-btn:disabled {
    color: #1a3a5c;
    background: #04080f;
    border: solid #0d2035;
}

#pipeline-area {
    height: 1fr;
    layout: horizontal;
}

.pipeline-panel {
    width: 1fr;
    border: solid #0d2035;
    background: #060d18;
    margin: 0 1 0 0;
    padding: 0;
}

.pipeline-panel.panel-active {
    border: solid #00d4ff;
}

.pipeline-panel.panel-pass {
    border: solid #00cc66;
}

.pipeline-panel.panel-fail {
    border: solid #ff3355;
}

.panel-header {
    height: 3;
    background: #04080f;
    border-bottom: solid #0d2035;
    padding: 0 2;
    align: left middle;
    layout: horizontal;
}

.panel-title {
    color: #00d4ff;
    text-style: bold;
    width: 1fr;
    content-align: left middle;
}

.panel-badge {
    width: auto;
    content-align: right middle;
}

.badge-idle {
    color: #1a3a5c;
}

.badge-running {
    color: #ffaa00;
}

.badge-done {
    color: #00ff99;
}

.badge-fail {
    color: #ff3355;
}

.panel-body {
    height: 1fr;
    padding: 1;
}

/* ── History view ────────────────────────────────────────── */
#history-table {
    height: 1fr;
    border: solid #0d2035;
    background: #060d18;
}

/* ── DataTable ───────────────────────────────────────────── */
DataTable {
    background: #060d18;
    color: #c8d8e8;
}

DataTable > .datatable--header {
    background: #04080f;
    color: #00d4ff;
    text-style: bold;
}

DataTable > .datatable--cursor {
    background: #0a2540;
    color: #00d4ff;
}

DataTable > .datatable--odd-row {
    background: #060d18;
}

DataTable > .datatable--even-row {
    background: #070e1a;
}

/* ── RichLog ─────────────────────────────────────────────── */
RichLog {
    background: transparent;
    color: #c8d8e8;
}

/* ── LoadingIndicator ────────────────────────────────────── */
LoadingIndicator {
    color: #00d4ff;
}

/* ── Footer ──────────────────────────────────────────────── */
Footer {
    background: #04080f;
    border-top: solid #0d2035;
    color: #2a4a6a;
}
"""


# ─────────────────────────────────────────────────────────────────────────────
# BACKEND CLIENT
# ─────────────────────────────────────────────────────────────────────────────

class BackendClient:
    """Thin async wrapper around the FastAPI backend."""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url.rstrip("/")

    async def health(self) -> bool:
        """Returns True if backend is reachable and healthy."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{self.base_url}/health")
                return r.status_code == 200
        except Exception:
            return False

    async def analyze(self, symbol: str) -> dict[str, Any]:
        """GET /analyze/{symbol} — research only."""
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            r = await client.get(f"{self.base_url}/analyze/{symbol}")
            r.raise_for_status()
            return r.json()

    async def critique(self, payload: dict) -> dict[str, Any]:
        """POST /critique — full 3-agent pipeline."""
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            r = await client.post(f"{self.base_url}/critique", json=payload)
            r.raise_for_status()
            return r.json()


# ─────────────────────────────────────────────────────────────────────────────
# HISTORY STORE
# ─────────────────────────────────────────────────────────────────────────────

class HistoryStore:
    """In-memory store for completed analysis runs."""

    def __init__(self):
        self._records: list[dict] = []

    def add(self, symbol: str, verdict: str, summary: str) -> None:
        self._records.append({
            "symbol": symbol,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "verdict": verdict,
            "summary": summary[:80] + ("…" if len(summary) > 80 else ""),
        })

    def all(self) -> list[dict]:
        return list(reversed(self._records))


# ─────────────────────────────────────────────────────────────────────────────
# HEADER BAR WIDGET
# ─────────────────────────────────────────────────────────────────────────────

class HeaderBar(Widget):
    """Top bar: app title, live clock, backend connection status."""

    DEFAULT_CSS = ""
    backend_ok: reactive[bool | None] = reactive(None)

    def compose(self) -> ComposeResult:
        yield Static("◈ AGENTIC QUANT SANDBOX", id="app-title")
        yield Static("│", id="header-sep-1")
        yield Static("", id="header-clock")
        yield Static("│", id="header-sep-2")
        yield Static("● CONNECTING…", id="backend-status")

    def on_mount(self) -> None:
        self.set_interval(1, self._tick_clock)

    def _tick_clock(self) -> None:
        now = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
        self.query_one("#header-clock", Static).update(now)

    def watch_backend_ok(self, ok: bool | None) -> None:
        w = self.query_one("#backend-status", Static)
        if ok is True:
            w.update("● BACKEND ONLINE")
            w.remove_class("status-err")
            w.add_class("status-ok")
        elif ok is False:
            w.update("● BACKEND OFFLINE")
            w.remove_class("status-ok")
            w.add_class("status-err")


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR NAVIGATION
# ─────────────────────────────────────────────────────────────────────────────

VIEWS = ["Dashboard", "Analyze", "History"]


class SidebarNav(Widget):
    """Left navigation sidebar."""

    active_view: reactive[str] = reactive("Dashboard")

    def compose(self) -> ComposeResult:
        yield Static("  NAV", id="sidebar-title")
        for v in VIEWS:
            btn = Button(f"  {v}", id=f"nav-{v.lower()}", classes="nav-item")
            yield btn

    def on_mount(self) -> None:
        self._highlight(self.active_view)

    def watch_active_view(self, view: str) -> None:
        self._highlight(view)

    def _highlight(self, view: str) -> None:
        for v in VIEWS:
            btn = self.query_one(f"#nav-{v.lower()}", Button)
            if v == view:
                btn.add_class("active")
            else:
                btn.remove_class("active")

    @on(Button.Pressed)
    def _nav_pressed(self, event: Button.Pressed) -> None:
        for v in VIEWS:
            if event.button.id == f"nav-{v.lower()}":
                self.active_view = v
                self.app.switch_view(v)
                break


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD VIEW
# ─────────────────────────────────────────────────────────────────────────────

class AgentCard(Static):
    """Single agent status card."""

    def __init__(self, name: str, description: str, card_id: str):
        super().__init__(id=card_id, classes="agent-card card-idle")
        self._name = name
        self._desc = description
        self._status = "IDLE"

    def render(self) -> str:
        return (
            f"[bold #00d4ff]{self._name}[/]\n"
            f"[#4a6a8a]{self._status}[/]\n"
            f"[#2a4a6a]{self._desc}[/]"
        )

    def set_state(self, state: str) -> None:
        """state: 'idle' | 'active' | 'error'"""
        self._status = {"idle": "IDLE", "active": "● RUNNING", "error": "✗ ERROR"}.get(state, "IDLE")
        self.remove_class("card-idle", "card-active", "card-error")
        self.add_class(f"card-{state}")
        self.refresh()


class DashboardView(Widget):
    """Dashboard: agent cards, recent feed, system info."""

    DEFAULT_CSS = ""

    def compose(self) -> ComposeResult:
        yield Static("  AGENT STATUS", classes="section-label")
        with Horizontal(id="agent-cards"):
            yield AgentCard("RESEARCH AGENT",  "Market analysis & hypothesis",    "card-research")
            yield AgentCard("CODEGEN AGENT",   "Vectorbt strategy generator",     "card-codegen")
            yield AgentCard("CRITIC AGENT",    "Risk & bias auditor",             "card-critic")
        with Horizontal(id="dash-bottom"):
            with ScrollableContainer(id="recent-feed"):
                yield Static("  RECENT ANALYSES", classes="section-label")
                yield RichLog(id="feed-log", markup=True, highlight=False, wrap=True)
            with Vertical(id="system-status"):
                yield Static("  SYSTEM", classes="section-label")
                yield Static(id="sys-backend")
                yield Static(id="sys-time")
                yield Static(id="sys-python")
                yield Static(id="sys-runs")

    def on_mount(self) -> None:
        self._refresh_sys()
        self.set_interval(5, self._refresh_sys)

    def _refresh_sys(self) -> None:
        import sys
        self.query_one("#sys-time",   Static).update(
            f"[#2a6080]TIME   [/] {datetime.now().strftime('%H:%M:%S')}")
        self.query_one("#sys-python", Static).update(
            f"[#2a6080]PYTHON [/] {sys.version.split()[0]}")

    def set_backend_status(self, ok: bool) -> None:
        lbl = "[#00ff99]ONLINE[/]" if ok else "[#ff4466]OFFLINE[/]"
        self.query_one("#sys-backend", Static).update(f"[#2a6080]BACKEND[/] {lbl}")

    def add_feed_entry(self, symbol: str, verdict: str, summary: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        color = "#00ff99" if verdict == "PASS" else "#ff3355"
        log = self.query_one("#feed-log", RichLog)
        log.write(
            f"[#1a5070]{ts}[/] [bold #00d4ff]{symbol:8}[/] "
            f"[{color}]{verdict:4}[/] [#4a6a8a]{summary[:60]}[/]"
        )

    def set_run_count(self, n: int) -> None:
        self.query_one("#sys-runs", Static).update(f"[#2a6080]RUNS   [/] {n}")

    def set_agent_state(self, agent: str, state: str) -> None:
        card_map = {"research": "card-research", "codegen": "card-codegen", "critic": "card-critic"}
        if agent in card_map:
            self.query_one(f"#{card_map[agent]}", AgentCard).set_state(state)


# ─────────────────────────────────────────────────────────────────────────────
# PIPELINE PANEL WIDGET
# ─────────────────────────────────────────────────────────────────────────────

class PipelinePanel(Widget):
    """A single agent panel in the Analyze view pipeline."""

    def __init__(self, title: str, panel_id: str):
        super().__init__(id=panel_id, classes="pipeline-panel")
        self._title = title
        self._badge = "IDLE"
        self._badge_class = "badge-idle"

    def compose(self) -> ComposeResult:
        with Horizontal(classes="panel-header"):
            yield Static(self._title, classes="panel-title")
            yield Static("IDLE", id=f"{self.id}-badge", classes="panel-badge badge-idle")
        with ScrollableContainer(classes="panel-body"):
            yield LoadingIndicator(id=f"{self.id}-spinner")
            yield RichLog(id=f"{self.id}-log", markup=True, highlight=True, wrap=True)

    def on_mount(self) -> None:
        self._spinner(False)

    def _spinner(self, show: bool) -> None:
        self.query_one(f"#{self.id}-spinner", LoadingIndicator).display = show

    def _set_badge(self, text: str, css_class: str) -> None:
        badge = self.query_one(f"#{self.id}-badge", Static)
        badge.update(text)
        badge.remove_class("badge-idle", "badge-running", "badge-done", "badge-fail")
        badge.add_class(css_class)

    def set_running(self) -> None:
        self.remove_class("panel-pass", "panel-fail", "panel-active")
        self.add_class("panel-active")
        self._set_badge("● RUNNING", "badge-running")
        self._spinner(True)
        log = self.query_one(f"#{self.id}-log", RichLog)
        log.clear()

    def set_done(self, content: str, verdict: str | None = None) -> None:
        self._spinner(False)
        self.remove_class("panel-active")
        if verdict == "PASS":
            self.add_class("panel-pass")
            self._set_badge("✓ PASS", "badge-done")
        elif verdict == "FAIL":
            self.add_class("panel-fail")
            self._set_badge("✗ FAIL", "badge-fail")
        else:
            self._set_badge("✓ DONE", "badge-done")
        log = self.query_one(f"#{self.id}-log", RichLog)
        log.write(content)

    def set_error(self, message: str) -> None:
        self._spinner(False)
        self.remove_class("panel-active")
        self.add_class("panel-fail")
        self._set_badge("✗ ERROR", "badge-fail")
        log = self.query_one(f"#{self.id}-log", RichLog)
        log.write(f"[bold #ff3355]ERROR[/]\n[#4a6a8a]{message}[/]")

    def reset(self) -> None:
        self.remove_class("panel-active", "panel-pass", "panel-fail")
        self._set_badge("IDLE", "badge-idle")
        self._spinner(False)
        log = self.query_one(f"#{self.id}-log", RichLog)
        log.clear()


# ─────────────────────────────────────────────────────────────────────────────
# ANALYZE VIEW
# ─────────────────────────────────────────────────────────────────────────────

class AnalyzeView(Widget):
    """Main interaction view: input + 3-agent pipeline display."""

    DEFAULT_CSS = ""

    BINDINGS = [
        Binding("/", "focus_input", "Focus Input", show=False),
    ]

    def compose(self) -> ComposeResult:
        with Horizontal(id="analyze-input-bar"):
            yield Static("[#00d4ff]TICKER[/]  ", classes="section-label")
            yield Input(
                placeholder="BTC-USD  ETH-USD  AAPL  TSLA …",
                id="ticker-input",
            )
            yield Button("▶  RUN ANALYSIS", id="run-btn")
        with Horizontal(id="pipeline-area"):
            yield PipelinePanel("◈ RESEARCH AGENT",  "panel-research")
            yield PipelinePanel("◈ CODEGEN AGENT",   "panel-codegen")
            yield PipelinePanel("◈ CRITIC AGENT",    "panel-critic")

    def on_mount(self) -> None:
        self.query_one("#ticker-input", Input).focus()

    def action_focus_input(self) -> None:
        self.query_one("#ticker-input", Input).focus()

    def on_focus(self) -> None:
        self.query_one("#ticker-input", Input).focus()

    @on(Button.Pressed, "#run-btn")
    def _on_run(self, _event: Button.Pressed) -> None:
        self._start_analysis()

    @on(Input.Submitted, "#ticker-input")
    def _on_submit(self, _event: Input.Submitted) -> None:
        self._start_analysis()

    def _start_analysis(self) -> None:
        symbol = self.query_one("#ticker-input", Input).value.strip().upper()
        if not symbol:
            return
        btn = self.query_one("#run-btn", Button)
        btn.disabled = True
        for p in ("panel-research", "panel-codegen", "panel-critic"):
            self.query_one(f"#{p}", PipelinePanel).reset()
        # Kick off the async worker (defined in QuantApp)
        self.app.run_pipeline(symbol)

    def set_running_done(self) -> None:
        self.query_one("#run-btn", Button).disabled = False


# ─────────────────────────────────────────────────────────────────────────────
# HISTORY VIEW
# ─────────────────────────────────────────────────────────────────────────────

class HistoryView(Widget):
    """Scrollable history table of all completed analyses."""

    DEFAULT_CSS = ""

    def compose(self) -> ComposeResult:
        yield Static("  ANALYSIS HISTORY", classes="section-label")
        table = DataTable(id="history-table", cursor_type="row")
        table.add_columns("SYMBOL", "TIMESTAMP", "VERDICT", "SUMMARY")
        yield table

    def refresh_history(self, records: list[dict]) -> None:
        table = self.query_one("#history-table", DataTable)
        table.clear()
        for rec in records:
            verdict_text = Text(rec["verdict"])
            if rec["verdict"] == "PASS":
                verdict_text.stylize("bold #00ff99")
            elif rec["verdict"] == "FAIL":
                verdict_text.stylize("bold #ff3355")
            else:
                verdict_text.stylize("#ffaa00")
            table.add_row(
                Text(rec["symbol"], style="#00d4ff bold"),
                Text(rec["timestamp"], style="#4a6a8a"),
                verdict_text,
                Text(rec["summary"], style="#c8d8e8"),
            )


# ─────────────────────────────────────────────────────────────────────────────
# ROOT APPLICATION
# ─────────────────────────────────────────────────────────────────────────────

class QuantApp(App):
    """Agentic Quant Sandbox — Bloomberg-style Textual TUI."""

    CSS = APP_CSS
    TITLE = "Agentic Quant Sandbox"

    BINDINGS = [
        Binding("q",   "quit",              "Quit"),
        Binding("tab", "focus_next",        "Next focus", show=False),
        Binding("1",   "nav_dashboard",     "Dashboard"),
        Binding("2",   "nav_analyze",       "Analyze"),
        Binding("3",   "nav_history",       "History"),
        Binding("r",   "refresh_backend",   "Refresh status"),
    ]

    def __init__(self):
        super().__init__()
        self._client = BackendClient()
        self._history = HistoryStore()
        self._current_view = "Dashboard"

    # ── Layout ────────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield HeaderBar(id="header-bar")
        with Horizontal(id="app-body"):
            yield SidebarNav(id="sidebar")
            with Container(id="main-content"):
                yield DashboardView(id="view-dashboard", classes="view")
                yield AnalyzeView(id="view-analyze",    classes="view")
                yield HistoryView(id="view-history",    classes="view")
        yield Footer()

    def on_mount(self) -> None:
        # Start with Dashboard
        self.switch_view("Dashboard")
        # Poll backend health on startup
        self.check_backend_health()
        # Periodic health check every 30 s
        self.set_interval(30, self.check_backend_health)

    # ── View switching ─────────────────────────────────────────────────────────

    def switch_view(self, view_name: str) -> None:
        """Show the requested view, hide the rest."""
        self._current_view = view_name
        for v in VIEWS:
            widget = self.query_one(f"#view-{v.lower()}")
            widget.display = (v == view_name)
        # Keep sidebar in sync
        self.query_one("#sidebar", SidebarNav).active_view = view_name
        # Focus input when switching to Analyze
        if view_name == "Analyze":
            self.query_one("#view-analyze", AnalyzeView).focus()
        # Refresh history table on every switch to History
        if view_name == "History":
            self.query_one("#view-history", HistoryView).refresh_history(
                self._history.all()
            )

    # ── Keybind actions ────────────────────────────────────────────────────────

    def action_nav_dashboard(self)  -> None: self.switch_view("Dashboard")
    def action_nav_analyze(self)    -> None: self.switch_view("Analyze")
    def action_nav_history(self)    -> None: self.switch_view("History")
    def action_refresh_backend(self) -> None: self.check_backend_health()

    # ── Backend health check ───────────────────────────────────────────────────

    @work(exclusive=True, thread=False)
    async def check_backend_health(self) -> None:
        ok = await self._client.health()
        self.query_one("#header-bar", HeaderBar).backend_ok = ok
        self.query_one("#view-dashboard", DashboardView).set_backend_status(ok)

    # ── Main analysis pipeline ─────────────────────────────────────────────────

    @work(exclusive=True, thread=False)
    async def run_pipeline(self, symbol: str) -> None:
        """
        Full 3-agent pipeline:
          1. GET /analyze/{symbol}     → Research panel
          2. POST /critique            → CodeGen + Critic panels
        """
        dashboard = self.query_one("#view-dashboard", DashboardView)
        analyze   = self.query_one("#view-analyze",   AnalyzeView)
        r_panel   = self.query_one("#panel-research",  PipelinePanel)
        c_panel   = self.query_one("#panel-codegen",   PipelinePanel)
        x_panel   = self.query_one("#panel-critic",    PipelinePanel)

        research_data: dict = {}
        final_verdict = "N/A"
        final_summary = ""

        # ── STEP 1: Research Agent ──────────────────────────────────────────
        r_panel.set_running()
        dashboard.set_agent_state("research", "active")
        try:
            result = await self._client.analyze(symbol)
            research_data = result
            ai_analysis = result.get("ai_analysis", "No analysis returned.")
            indicators  = result.get("live_indicators", {})

            ind_block = self._format_indicators(indicators)
            r_panel.set_done(
                f"[bold #00d4ff]SYMBOL:[/] {symbol}\n\n"
                f"[#1a5070]─── INDICATORS ─────────────────[/]\n"
                f"{ind_block}\n\n"
                f"[#1a5070]─── AI ANALYSIS ────────────────[/]\n"
                f"[#c8d8e8]{ai_analysis}[/]"
            )
            dashboard.set_agent_state("research", "idle")

        except httpx.ConnectError:
            r_panel.set_error("Cannot connect to backend. Is the FastAPI server running?")
            dashboard.set_agent_state("research", "error")
            analyze.set_running_done()
            return
        except httpx.HTTPStatusError as e:
            r_panel.set_error(f"HTTP {e.response.status_code}: {e.response.text[:300]}")
            dashboard.set_agent_state("research", "error")
            analyze.set_running_done()
            return
        except Exception as e:
            r_panel.set_error(str(e))
            dashboard.set_agent_state("research", "error")
            analyze.set_running_done()
            return

        # ── STEP 2: CodeGen + Critic (POST /critique) ───────────────────────
        c_panel.set_running()
        dashboard.set_agent_state("codegen", "active")

        # Build the payload /critique expects (same shape as POST /analyze body)
        indicators = research_data.get("live_indicators", {})
        ema20 = indicators.get("EMA20")
        ema50 = indicators.get("EMA50")
        trend = "Bullish (EMA20 > EMA50)" if (ema20 and ema50 and ema20 > ema50) else "Bearish (EMA20 < EMA50)"

        critique_payload = {
            "symbol":       symbol,
            "price":        indicators.get("current_price"),
            "rsi":          indicators.get("RSI"),
            "macd":         (
                f"Line: {indicators.get('MACD', 0):.4f}, "
                f"Signal: {indicators.get('MACD_signal', 0):.4f}"
            ),
            "volume_trend": (
                f"Trend: {trend} | "
                f"EMA20: {ema20:.2f if ema20 else 'N/A'} | "
                f"EMA50: {ema50:.2f if ema50 else 'N/A'} | "
                f"ATR: {indicators.get('ATR', 0):.4f}"
            ),
        }

        try:
            full = await self._client.critique(critique_payload)

            # CodeGen panel
            code     = full.get("generated_code", {}).get("code", "# No code generated.")
            c_panel.set_done(self._format_code(code))
            dashboard.set_agent_state("codegen", "idle")

            # Critic panel
            x_panel.set_running()
            dashboard.set_agent_state("critic", "active")

            critique = full.get("critique", {})
            verdict     = critique.get("verdict", "N/A")
            issues      = critique.get("issues", [])
            suggestions = critique.get("suggestions", [])
            final_verdict = verdict
            final_summary = research_data.get("ai_analysis", "")[:80]

            x_panel.set_done(
                self._format_critique(verdict, issues, suggestions),
                verdict=verdict,
            )
            dashboard.set_agent_state("critic", "idle")

        except httpx.ConnectError:
            c_panel.set_error("Cannot connect to backend.")
            dashboard.set_agent_state("codegen", "error")
            analyze.set_running_done()
            return
        except httpx.HTTPStatusError as e:
            c_panel.set_error(f"HTTP {e.response.status_code}: {e.response.text[:300]}")
            dashboard.set_agent_state("codegen", "error")
            analyze.set_running_done()
            return
        except Exception as e:
            c_panel.set_error(str(e))
            dashboard.set_agent_state("codegen", "error")
            analyze.set_running_done()
            return

        # ── Record in history ───────────────────────────────────────────────
        self._history.add(symbol, final_verdict, final_summary)
        dashboard.add_feed_entry(symbol, final_verdict, final_summary)
        dashboard.set_run_count(len(self._history.all()))
        analyze.set_running_done()

    # ── Formatting helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _format_indicators(ind: dict) -> str:
        if not ind:
            return "[#4a6a8a]No indicator data.[/]"
        lines = []
        fields = [
            ("PRICE",       "current_price",  ".4f"),
            ("RSI",         "RSI",            ".2f"),
            ("MACD",        "MACD",           ".6f"),
            ("MACD_SIG",    "MACD_signal",    ".6f"),
            ("EMA 20",      "EMA20",          ".4f"),
            ("EMA 50",      "EMA50",          ".4f"),
            ("ATR",         "ATR",            ".4f"),
        ]
        for label, key, fmt in fields:
            val = ind.get(key)
            if val is not None:
                try:
                    formatted = format(float(val), fmt)
                except (TypeError, ValueError):
                    formatted = str(val)
                lines.append(f"[#2a6080]{label:<10}[/] [#c8d8e8]{formatted}[/]")
        return "\n".join(lines) if lines else "[#4a6a8a]No data.[/]"

    @staticmethod
    def _format_code(code: str) -> str:
        """Wrap code in Rich markup for monospace display."""
        # Strip markdown fences if present
        lines = code.strip().splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        clean = "\n".join(lines)
        # Highlight keywords minimally for a premium terminal feel
        return f"[#4a9a6a]{clean}[/]"

    @staticmethod
    def _format_critique(verdict: str, issues: list, suggestions: list) -> str:
        v_color  = "#00ff99" if verdict == "PASS" else "#ff3355"
        lines = [
            f"[bold {v_color}]VERDICT: {verdict}[/]\n",
            "[#1a5070]─── ISSUES ──────────────────────[/]",
        ]
        if issues:
            for i, issue in enumerate(issues, 1):
                lines.append(f"[#ff8844]{i}.[/] [#c8d8e8]{issue}[/]")
        else:
            lines.append("[#4a6a8a]None detected.[/]")

        lines.append("\n[#1a5070]─── SUGGESTIONS ─────────────────[/]")
        if suggestions:
            for i, sug in enumerate(suggestions, 1):
                lines.append(f"[#00aaff]{i}.[/] [#c8d8e8]{sug}[/]")
        else:
            lines.append("[#4a6a8a]None.[/]")

        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = QuantApp()
    app.run()
