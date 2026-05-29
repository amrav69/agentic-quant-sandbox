// ═══════════════════════════════════════════════════════════════════════════
//  Agentic Quant Sandbox — Ratatui Terminal Application
//  Bloomberg Terminal × Institutional Quant Research × AI Agent Console
// ═══════════════════════════════════════════════════════════════════════════

use anyhow::{Context, Result};
use chrono::Local;
use crossterm::{
    event::{self, DisableMouseCapture, EnableMouseCapture, Event, KeyCode, KeyEventKind, KeyModifiers},
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use futures_util::StreamExt;
use ratatui::{
    backend::CrosstermBackend,
    layout::{Alignment, Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{
        Block, BorderType, Borders, Cell, List, ListItem, Paragraph, Row,
        ScrollbarState, Table, TableState, Wrap,
    },
    Frame, Terminal,
};
use serde::{Deserialize, Serialize};
use std::{
    io,
    time::{Duration, Instant},
};
use tokio::sync::mpsc;

// ─────────────────────────────────────────────────────────────────────────────
// CONSTANTS
// ─────────────────────────────────────────────────────────────────────────────

const BACKEND_URL: &str = "http://127.0.0.1:8000";
const HEALTH_CHECK_INTERVAL_MS: u64 = 5000;
const TICK_RATE_MS: u64 = 50; // ~20 FPS event polling

// ─────────────────────────────────────────────────────────────────────────────
// COLOUR PALETTE — Bloomberg-inspired professional dark theme
// ─────────────────────────────────────────────────────────────────────────────

const C_BG: Color = Color::Rgb(5, 8, 16);
const C_BG_PANEL: Color = Color::Rgb(6, 13, 24);
const C_BG_HEADER: Color = Color::Rgb(8, 15, 26);
const C_BORDER: Color = Color::Rgb(13, 32, 53);
const C_PRIMARY: Color = Color::Rgb(0, 212, 255); // cyan
const C_SECONDARY: Color = Color::Rgb(140, 80, 255); // purple
const C_SUCCESS: Color = Color::Rgb(0, 255, 153); // green
const C_ERROR: Color = Color::Rgb(255, 51, 85); // red
const C_WARNING: Color = Color::Rgb(255, 170, 0); // amber
const C_TEXT: Color = Color::Rgb(200, 216, 232);
const C_TEXT_DIM: Color = Color::Rgb(74, 106, 138);
const C_TEXT_MUTED: Color = Color::Rgb(30, 58, 92);
const C_HIGHLIGHT: Color = Color::Rgb(10, 37, 64);

// ─────────────────────────────────────────────────────────────────────────────
// ENUMS — Views, Agent States, Loading States
// ─────────────────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, PartialEq)]
enum View {
    Dashboard,
    Analyze,
    History,
}

#[derive(Debug, Clone, PartialEq)]
enum AgentState {
    Idle,
    Running,
    Done,
    Error,
}

#[derive(Debug, Clone, PartialEq)]
enum LoadingState {
    Idle,
    FetchingResearch,
    FetchingCodeGen,
    FetchingCritic,
    Complete,
    Error(String),
}

#[derive(Debug, Clone, PartialEq)]
enum BackendStatus {
    Unknown,
    Online,
    Offline,
}

// ─────────────────────────────────────────────────────────────────────────────
// MESSAGES — Async channel messages from background tasks → UI
// ─────────────────────────────────────────────────────────────────────────────

#[derive(Debug)]
enum AppMessage {
    HealthCheckResult(bool),
    ResearchResult(String),
    CodeGenResult(String),
    CriticResult(CritiqueResult),
    StreamEvent(StreamStage, String),
    PipelineError(String),
    ClockTick,
}

#[derive(Debug, Clone)]
enum StreamStage {
    Research,
    CodeGen,
    Critic,
    Error,
}

// ─────────────────────────────────────────────────────────────────────────────
// API RESPONSE TYPES
// ─────────────────────────────────────────────────────────────────────────────

// GET /analyze/{symbol}
// live_indicators uses both "current price" (space) and "current_price" (underscore)
// ai_analysis is a JSON-escaped string — must be parsed as String then re-decoded
#[allow(dead_code)]
#[derive(Debug, Deserialize, Clone)]
struct AnalyzeResponse {
    symbol: String,
    /// Raw JSON string from ResearchAgent — parse separately with serde_json::from_str
    ai_analysis: Option<String>,
    live_indicators: Option<LiveIndicators>,
}

/// Covers both snake_case and space-separated field variants the backend emits
#[allow(dead_code)]
#[derive(Debug, Deserialize, Clone, Default)]
struct LiveIndicators {
    symbol: Option<String>,
    /// backend emits both "current_price" and "current price" — primary field
    current_price: Option<f64>,
    #[serde(rename = "current price")]
    current_price_spaced: Option<f64>,
    #[serde(rename = "RSI")]
    rsi: Option<f64>,
    #[serde(rename = "MACD")]
    macd: Option<f64>,
    /// snake_case variant
    #[serde(rename = "MACD_signal")]
    macd_signal: Option<f64>,
    /// space variant
    #[serde(rename = "MACD signal")]
    macd_signal_spaced: Option<f64>,
    #[serde(rename = "EMA20")]
    ema20: Option<f64>,
    #[serde(rename = "EMA50")]
    ema50: Option<f64>,
    #[serde(rename = "ATR")]
    atr: Option<f64>,
}

impl LiveIndicators {
    /// Returns the best available current price from either field variant
    fn price(&self) -> Option<f64> {
        self.current_price.or(self.current_price_spaced)
    }
    fn macd_signal(&self) -> Option<f64> {
        self.macd_signal.or(self.macd_signal_spaced)
    }
}

// POST /critique
#[allow(dead_code)]
#[derive(Debug, Deserialize, Clone)]
struct CritiqueApiResponse {
    research_analysis: Option<serde_json::Value>,
    generated_code: Option<GeneratedCode>,
    critique: Option<CritiqueResult>,
}

/// backend returns code wrapped in markdown fences (```python ... ```)
#[allow(dead_code)]
#[derive(Debug, Deserialize, Clone)]
struct GeneratedCode {
    agent: Option<String>,
    code: Option<String>,
    based_on: Option<String>,
}

impl GeneratedCode {
    /// Strip markdown code fences so raw Python is displayed cleanly
    fn clean_code(&self) -> String {
        let Some(code) = &self.code else { return String::new() };
        let stripped = code
            .trim()
            .strip_prefix("```python")
            .or_else(|| code.trim().strip_prefix("```"))
            .unwrap_or(code)
            .trim_start_matches('\n');
        let stripped = stripped
            .strip_suffix("```")
            .unwrap_or(stripped)
            .trim_end();
        stripped.to_string()
    }
}

/// critique.issues is Vec<{severity, issue}> objects, NOT Vec<String>
#[allow(dead_code)]
#[derive(Debug, Deserialize, Clone)]
struct CritiqueIssue {
    severity: Option<String>,
    issue: String,
}

/// critique.suggestions may be strings or objects — use Value and coerce
#[derive(Debug, Deserialize, Clone, Default)]
struct CritiqueResult {
    #[allow(dead_code)]
    agent: Option<String>,
    verdict: Option<String>,
    /// objects: [{severity, issue}] — extracted into display strings
    #[serde(default)]
    issues: Option<Vec<CritiqueIssue>>,
    /// may be absent or an array of strings or objects
    #[serde(default)]
    suggestions: Option<Vec<serde_json::Value>>,
    confidence: Option<f64>,
}

impl CritiqueResult {
    fn issue_strings(&self) -> Vec<String> {
        self.issues.as_deref().unwrap_or(&[]).iter().map(|i| {
            let prefix = i.severity.as_deref()
                .map(|s| format!("[{}] ", s.to_uppercase()))
                .unwrap_or_default();
            format!("{}{}", prefix, i.issue)
        }).collect()
    }

    fn suggestion_strings(&self) -> Vec<String> {
        self.suggestions.as_deref().unwrap_or(&[]).iter().map(|v| {
            match v {
                serde_json::Value::String(s) => s.clone(),
                serde_json::Value::Object(m) => {
                    // handle {suggestion: "..."} or {text: "..."}
                    m.get("suggestion")
                        .or_else(|| m.get("text"))
                        .or_else(|| m.get("issue"))
                        .and_then(|v| v.as_str())
                        .unwrap_or("")
                        .to_string()
                }
                other => other.to_string(),
            }
        }).collect()
    }
}

#[derive(Debug, Deserialize)]
struct SseEvent {
    stage: Option<String>,
    status: Option<String>,
    result: Option<serde_json::Value>,
    message: Option<String>,
}

#[derive(Debug, Serialize)]
struct CritiqueRequest {
    symbol: String,
    price: Option<f64>,
    rsi: Option<f64>,
    macd: Option<String>,
    volume_trend: Option<String>,
}

// ─────────────────────────────────────────────────────────────────────────────
// HISTORY ENTRY
// ─────────────────────────────────────────────────────────────────────────────

#[derive(Debug, Clone)]
struct HistoryEntry {
    symbol: String,
    regime: String,
    verdict: String,
    confidence: String,
    timestamp: String,
}

// ─────────────────────────────────────────────────────────────────────────────
// AGENT STATUS
// ─────────────────────────────────────────────────────────────────────────────

#[derive(Debug, Clone)]
struct AgentStatus {
    name: String,
    description: String,
    state: AgentState,
    last_activity: String,
}

impl AgentStatus {
    fn new(name: &str, description: &str) -> Self {
        Self {
            name: name.to_string(),
            description: description.to_string(),
            state: AgentState::Idle,
            last_activity: "Never".to_string(),
        }
    }

    fn state_label(&self) -> &str {
        match self.state {
            AgentState::Idle => "IDLE",
            AgentState::Running => "● RUNNING",
            AgentState::Done => "✓ DONE",
            AgentState::Error => "✗ ERROR",
        }
    }

    fn state_color(&self) -> Color {
        match self.state {
            AgentState::Idle => C_TEXT_DIM,
            AgentState::Running => C_WARNING,
            AgentState::Done => C_SUCCESS,
            AgentState::Error => C_ERROR,
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// APP STATE — Central application state
// ─────────────────────────────────────────────────────────────────────────────

struct App {
    // Navigation
    active_view: View,

    // Backend
    backend_status: BackendStatus,
    last_response_time: Option<String>,

    // Clock
    clock: String,
    last_health_check: Instant,

    // Ticker input
    ticker_input: String,
    input_cursor_position: usize,

    // Pipeline state
    loading_state: LoadingState,
    research_output: String,
    codegen_output: String,
    critic_output: CritiqueResult,
    current_symbol: String,

    // Agent statuses
    agents: Vec<AgentStatus>,

    // History
    history: Vec<HistoryEntry>,
    history_table_state: TableState,
    history_scroll_state: ScrollbarState,

    // Feed log (recent analyses on dashboard)
    feed_log: Vec<String>,

    // Research scroll
    research_scroll: u16,
    codegen_scroll: u16,
    critic_scroll: u16,

    // Async channel
    msg_tx: mpsc::UnboundedSender<AppMessage>,

    // Quit flag
    should_quit: bool,
}

impl App {
    fn new(msg_tx: mpsc::UnboundedSender<AppMessage>) -> Self {
        let agents = vec![
            AgentStatus::new("RESEARCH AGENT", "Market analysis & hypothesis"),
            AgentStatus::new("CODEGEN AGENT", "VectorBT strategy generator"),
            AgentStatus::new("CRITIC AGENT", "Risk & bias auditor"),
        ];

        Self {
            active_view: View::Dashboard,
            backend_status: BackendStatus::Unknown,
            last_response_time: None,
            clock: Local::now().format("%Y-%m-%d  %H:%M:%S").to_string(),
            last_health_check: Instant::now() - Duration::from_secs(10),
            ticker_input: String::new(),
            input_cursor_position: 0,
            loading_state: LoadingState::Idle,
            research_output: String::new(),
            codegen_output: String::new(),
            critic_output: CritiqueResult::default(),
            current_symbol: String::new(),
            agents,
            history: Vec::new(),
            history_table_state: TableState::default(),
            history_scroll_state: ScrollbarState::default(),
            feed_log: Vec::new(),
            research_scroll: 0,
            codegen_scroll: 0,
            critic_scroll: 0,
            msg_tx,
            should_quit: false,
        }
    }

    // ── Input handling ─────────────────────────────────────────────────────

    fn input_push(&mut self, c: char) {
        // Allow alphanumeric, hyphen, dot
        if c.is_alphanumeric() || c == '-' || c == '.' {
            let idx = self.byte_index_at_cursor();
            self.ticker_input.insert(idx, c.to_ascii_uppercase());
            self.input_cursor_position += 1;
        }
    }

    fn input_backspace(&mut self) {
        if self.input_cursor_position > 0 {
            let idx = self.byte_index_at_cursor();
            let prev_char_len = self.ticker_input[..idx].chars().last().map_or(0, |c| c.len_utf8());
            if prev_char_len > 0 {
                self.ticker_input.drain(idx - prev_char_len..idx);
                self.input_cursor_position -= 1;
            }
        }
    }

    fn input_delete(&mut self) {
        let idx = self.byte_index_at_cursor();
        if idx < self.ticker_input.len() {
            let next_char_len = self.ticker_input[idx..].chars().next().map_or(0, |c| c.len_utf8());
            self.ticker_input.drain(idx..idx + next_char_len);
        }
    }

    fn cursor_left(&mut self) {
        self.input_cursor_position = self.input_cursor_position.saturating_sub(1);
    }

    fn cursor_right(&mut self) {
        let max = self.ticker_input.chars().count();
        if self.input_cursor_position < max {
            self.input_cursor_position += 1;
        }
    }

    fn byte_index_at_cursor(&self) -> usize {
        self.ticker_input
            .char_indices()
            .nth(self.input_cursor_position)
            .map(|(i, _)| i)
            .unwrap_or(self.ticker_input.len())
    }

    fn input_with_cursor(&self) -> String {
        let mut s = self.ticker_input.clone();
        let idx = self.byte_index_at_cursor();
        s.insert(idx, '│'); // cursor marker
        s
    }

    // ── View switching ─────────────────────────────────────────────────────

    fn switch_view(&mut self, view: View) {
        self.active_view = view;
        if self.active_view == View::History {
            let len = self.history.len();
            self.history_scroll_state = self.history_scroll_state.content_length(len);
        }
    }

    // ── History navigation ─────────────────────────────────────────────────

    fn history_next(&mut self) {
        let i = match self.history_table_state.selected() {
            Some(i) => (i + 1).min(self.history.len().saturating_sub(1)),
            None => 0,
        };
        self.history_table_state.select(Some(i));
        self.history_scroll_state = self.history_scroll_state.position(i);
    }

    fn history_prev(&mut self) {
        let i = match self.history_table_state.selected() {
            Some(i) => i.saturating_sub(1),
            None => 0,
        };
        self.history_table_state.select(Some(i));
        self.history_scroll_state = self.history_scroll_state.position(i);
    }

    // ── State updates from messages ────────────────────────────────────────

    fn apply_message(&mut self, msg: AppMessage) {
        match msg {
            AppMessage::ClockTick => {
                self.clock = Local::now().format("%Y-%m-%d  %H:%M:%S").to_string();
            }

            AppMessage::HealthCheckResult(ok) => {
                self.backend_status = if ok { BackendStatus::Online } else { BackendStatus::Offline };
                self.last_health_check = Instant::now();
                self.last_response_time = Some(Local::now().format("%H:%M:%S").to_string());
            }

            AppMessage::ResearchResult(text) => {
                self.research_output = text;
                self.loading_state = LoadingState::FetchingCodeGen;
                self.agents[0].state = AgentState::Done;
                self.agents[0].last_activity = Local::now().format("%H:%M:%S").to_string();
                self.agents[1].state = AgentState::Running;
            }

            AppMessage::CodeGenResult(code) => {
                self.codegen_output = code;
                self.loading_state = LoadingState::FetchingCritic;
                self.agents[1].state = AgentState::Done;
                self.agents[1].last_activity = Local::now().format("%H:%M:%S").to_string();
                self.agents[2].state = AgentState::Running;
            }

            AppMessage::CriticResult(result) => {
                let verdict = result.verdict.clone().unwrap_or_default();
                let confidence = result.confidence.map(|c| format!("{:.0}%", c * 100.0))
                    .unwrap_or_else(|| "N/A".to_string());
                self.critic_output = result;
                self.loading_state = LoadingState::Complete;
                self.agents[2].state = AgentState::Done;
                self.agents[2].last_activity = Local::now().format("%H:%M:%S").to_string();

                // Add to history
                let ts = Local::now().format("%Y-%m-%d %H:%M:%S").to_string();
                let entry = HistoryEntry {
                    symbol: self.current_symbol.clone(),
                    regime: extract_regime(&self.research_output),
                    verdict: verdict.clone(),
                    confidence: confidence.clone(),
                    timestamp: ts.clone(),
                };
                self.history.push(entry);

                // Feed log entry
                let color_tag = if verdict == "PASS" { "✓" } else { "✗" };
                self.feed_log.push(format!(
                    "[{}]  {:8}  {}  conf: {}",
                    ts, self.current_symbol, color_tag, confidence
                ));
                if self.feed_log.len() > 100 {
                    self.feed_log.remove(0);
                }

                // Update agent cards
                for a in self.agents.iter_mut() {
                    if a.state != AgentState::Error {
                        a.state = AgentState::Idle;
                    }
                }
            }

            AppMessage::StreamEvent(stage, data) => {
                match stage {
                    StreamStage::Research => {
                        self.loading_state = LoadingState::FetchingResearch;
                        self.agents[0].state = AgentState::Running;
                        if !data.is_empty() {
                            self.research_output = data;
                            self.agents[0].state = AgentState::Done;
                            self.agents[0].last_activity = Local::now().format("%H:%M:%S").to_string();
                        }
                    }
                    StreamStage::CodeGen => {
                        self.loading_state = LoadingState::FetchingCodeGen;
                        self.agents[1].state = AgentState::Running;
                        if !data.is_empty() {
                            self.codegen_output = data;
                            self.agents[1].state = AgentState::Done;
                            self.agents[1].last_activity = Local::now().format("%H:%M:%S").to_string();
                        }
                    }
                    StreamStage::Critic => {
                        self.loading_state = LoadingState::FetchingCritic;
                        self.agents[2].state = AgentState::Running;
                        if !data.is_empty() {
                            // parse critic JSON
                            if let Ok(cr) = serde_json::from_str::<CritiqueResult>(&data) {
                                let msg = AppMessage::CriticResult(cr);
                                let _ = self.msg_tx.send(msg);
                            }
                        }
                    }
                    StreamStage::Error => {
                        self.loading_state = LoadingState::Error(data);
                        for a in self.agents.iter_mut() {
                            if a.state == AgentState::Running {
                                a.state = AgentState::Error;
                            }
                        }
                    }
                }
            }

            AppMessage::PipelineError(err) => {
                self.loading_state = LoadingState::Error(err.clone());
                for a in self.agents.iter_mut() {
                    if a.state == AgentState::Running {
                        a.state = AgentState::Error;
                        a.last_activity = format!("Error: {}", &err[..err.len().min(40)]);
                    }
                }
            }
        }
    }

    // ── Trigger analysis ───────────────────────────────────────────────────

    fn run_analysis(&mut self) {
        let symbol = self.ticker_input.trim().to_uppercase();
        if symbol.is_empty() {
            return;
        }
        self.current_symbol = symbol.clone();
        self.loading_state = LoadingState::FetchingResearch;
        self.research_output = String::new();
        self.codegen_output = String::new();
        self.critic_output = CritiqueResult::default();
        self.research_scroll = 0;
        self.codegen_scroll = 0;
        self.critic_scroll = 0;

        for a in self.agents.iter_mut() {
            a.state = AgentState::Idle;
        }
        self.agents[0].state = AgentState::Running;

        let tx = self.msg_tx.clone();
        tokio::spawn(run_pipeline(symbol, tx));
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// HELPERS
// ─────────────────────────────────────────────────────────────────────────────

fn extract_regime(research: &str) -> String {
    // Simple heuristic: look for known keywords
    for word in &["Bullish", "Bearish", "Ranging", "Neutral"] {
        if research.contains(word) {
            return word.to_string();
        }
    }
    "Unknown".to_string()
}

fn spinner_frame(instant: &Instant) -> &'static str {
    let frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];
    let i = (instant.elapsed().as_millis() / 100) as usize % frames.len();
    frames[i]
}

// ─────────────────────────────────────────────────────────────────────────────
// BACKEND NETWORKING — Async API calls
// ─────────────────────────────────────────────────────────────────────────────

async fn check_health() -> bool {
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(3))
        .build()
        .unwrap_or_default();
    client.get(format!("{}/health", BACKEND_URL))
        .send()
        .await
        .map(|r| r.status().is_success())
        .unwrap_or(false)
}

async fn run_pipeline(symbol: String, tx: mpsc::UnboundedSender<AppMessage>) {
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(90))
        .build()
        .unwrap_or_default();

    // Try SSE streaming first; fall back to regular HTTP
    let sse_result = run_sse_pipeline(&client, &symbol, &tx).await;
    if sse_result.is_err() {
        run_http_pipeline(&client, &symbol, &tx).await;
    }
}

async fn run_sse_pipeline(
    client: &reqwest::Client,
    symbol: &str,
    tx: &mpsc::UnboundedSender<AppMessage>,
) -> Result<()> {
    let payload = CritiqueRequest {
        symbol: symbol.to_string(),
        price: None,
        rsi: None,
        macd: None,
        volume_trend: None,
    };

    let resp = client
        .post(format!("{}/analyze/stream", BACKEND_URL))
        .json(&payload)
        .send()
        .await
        .context("SSE connect failed")?;

    if !resp.status().is_success() {
        anyhow::bail!("SSE non-200: {}", resp.status());
    }

    let mut stream = resp.bytes_stream();
    let mut buffer = String::new();

    while let Some(chunk) = stream.next().await {
        let bytes = chunk.context("SSE read failed")?;
        buffer.push_str(&String::from_utf8_lossy(&bytes));

        // Drain complete SSE events (terminated by \n\n)
        while let Some(pos) = buffer.find("\n\n") {
            let event_text = buffer[..pos].to_string();
            buffer.drain(..pos + 2);

            // SSE lines start with "data: "
            for line in event_text.lines() {
                let data = line.strip_prefix("data: ").unwrap_or(line);
                if data.is_empty() {
                    continue;
                }
                if let Ok(evt) = serde_json::from_str::<SseEvent>(data) {
                    handle_sse_event(evt, tx);
                }
            }
        }
    }

    Ok(())
}

fn handle_sse_event(evt: SseEvent, tx: &mpsc::UnboundedSender<AppMessage>) {
    let stage_str = evt.stage.as_deref().unwrap_or("");
    let status = evt.status.as_deref().unwrap_or("");

    if stage_str == "error" {
        let msg = evt.message.unwrap_or_else(|| "Unknown SSE error".to_string());
        let _ = tx.send(AppMessage::StreamEvent(StreamStage::Error, msg));
        return;
    }

    if status == "running" {
        let stage = match stage_str {
            "research" => StreamStage::Research,
            "codegen" => StreamStage::CodeGen,
            "critic" => StreamStage::Critic,
            _ => return,
        };
        let _ = tx.send(AppMessage::StreamEvent(stage, String::new()));
    } else if status == "done" {
        if let Some(result) = evt.result {
            match stage_str {
                "research" => {
                    let text = result.get("analysis")
                        .and_then(|v| v.as_str())
                        .unwrap_or("")
                        .to_string();
                    let _ = tx.send(AppMessage::StreamEvent(StreamStage::Research, text));
                }
                "codegen" => {
                    let code = result.get("code")
                        .and_then(|v| v.as_str())
                        .unwrap_or("")
                        .to_string();
                    let _ = tx.send(AppMessage::StreamEvent(StreamStage::CodeGen, code));
                }
                "critic" => {
                    if let Ok(cr) = serde_json::from_value::<CritiqueResult>(result) {
                        let _ = tx.send(AppMessage::CriticResult(cr));
                    }
                }
                _ => {}
            }
        }
    }
}

async fn run_http_pipeline(
    client: &reqwest::Client,
    symbol: &str,
    tx: &mpsc::UnboundedSender<AppMessage>,
) {
    // Step 1: GET /analyze/{symbol}
    let analyze_url = format!("{}/analyze/{}", BACKEND_URL, symbol);
    match client.get(&analyze_url).send().await {
        Err(e) => {
            let _ = tx.send(AppMessage::PipelineError(format!("Research fetch failed: {}", e)));
            return;
        }
        Ok(resp) => match resp.json::<AnalyzeResponse>().await {
            Err(e) => {
                let _ = tx.send(AppMessage::PipelineError(format!("Research parse failed: {}", e)));
                return;
            }
            Ok(data) => {
                // ai_analysis is a JSON-escaped string — display it as-is
                // (try to pretty-print if it's valid JSON, else show raw)
                let raw_analysis = data.ai_analysis.unwrap_or_default();
                let analysis_display = if let Ok(v) = serde_json::from_str::<serde_json::Value>(&raw_analysis) {
                    // Format the nested JSON object into readable key: value lines
                    v.as_object()
                        .map(|m| {
                            m.iter()
                                .filter(|(k, _)| k.as_str() != "agent")
                                .map(|(k, v)| {
                                    let val = match v {
                                        serde_json::Value::String(s) => s.clone(),
                                        other => other.to_string(),
                                    };
                                    format!("{}: {}", k, val)
                                })
                                .collect::<Vec<_>>()
                                .join("\n")
                        })
                        .unwrap_or(raw_analysis.clone())
                } else {
                    raw_analysis.clone()
                };
                let _ = tx.send(AppMessage::ResearchResult(analysis_display));

                // Extract indicators using the typed LiveIndicators struct
                let ind = data.live_indicators.as_ref();
                let price = ind.and_then(|v| v.price());
                let rsi   = ind.and_then(|v| v.rsi);
                let macd_line = ind.and_then(|v| v.macd).unwrap_or(0.0);
                let macd_sig  = ind.and_then(|v| v.macd_signal()).unwrap_or(0.0);
                let ema20 = ind.and_then(|v| v.ema20).unwrap_or(0.0);
                let ema50 = ind.and_then(|v| v.ema50).unwrap_or(0.0);
                let atr   = ind.and_then(|v| v.atr).unwrap_or(0.0);

                let trend = if ema20 > ema50 { "Bullish (EMA20>EMA50)" } else { "Bearish (EMA20<EMA50)" };
                let volume_trend = format!(
                    "Trend: {} | EMA20: {:.2} | EMA50: {:.2} | ATR: {:.4}",
                    trend, ema20, ema50, atr
                );

                // Step 2: POST /critique
                let critique_payload = CritiqueRequest {
                    symbol: symbol.to_string(),
                    price,
                    rsi,
                    macd: Some(format!("Line: {:.4}, Signal: {:.4}", macd_line, macd_sig)),
                    volume_trend: Some(volume_trend),
                };

                match client
                    .post(format!("{}/critique", BACKEND_URL))
                    .json(&critique_payload)
                    .send()
                    .await
                {
                    Err(e) => {
                        let _ = tx.send(AppMessage::PipelineError(format!("Critique fetch failed: {}", e)));
                    }
                    Ok(cr_resp) => match cr_resp.json::<CritiqueApiResponse>().await {
                        Err(e) => {
                            let _ = tx.send(AppMessage::PipelineError(format!("Critique parse failed: {}", e)));
                        }
                        Ok(cr_data) => {
                            // Strip markdown fences from generated code
                            if let Some(code_obj) = cr_data.generated_code {
                                let code = code_obj.clean_code();
                                let _ = tx.send(AppMessage::CodeGenResult(code));
                            }
                            if let Some(critique) = cr_data.critique {
                                let _ = tx.send(AppMessage::CriticResult(critique));
                            }
                        }
                    },
                }
            }
        },
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// RENDERING — All UI drawing functions
// ─────────────────────────────────────────────────────────────────────────────

fn render(f: &mut Frame, app: &mut App, spinner_tick: &Instant) {
    let bg = Block::default().style(Style::default().bg(C_BG));
    f.render_widget(bg, f.size());

    let root = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3), // header
            Constraint::Min(1),    // body
            Constraint::Length(1), // footer
        ])
        .split(f.size());

    render_header(f, app, root[0]);

    let body = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Length(20), // sidebar
            Constraint::Min(1),     // content
        ])
        .split(root[1]);

    render_sidebar(f, app, body[0]);

    match app.active_view {
        View::Dashboard => render_dashboard(f, app, spinner_tick, body[1]),
        View::Analyze => render_analyze(f, app, spinner_tick, body[1]),
        View::History => render_history(f, app, body[1]),
    }

    render_footer(f, app, root[2]);
}

// ── Header ─────────────────────────────────────────────────────────────────

fn render_header(f: &mut Frame, app: &App, area: Rect) {
    let (status_label, status_color) = match app.backend_status {
        BackendStatus::Online => ("● ONLINE ", C_SUCCESS),
        BackendStatus::Offline => ("● OFFLINE", C_ERROR),
        BackendStatus::Unknown => ("● UNKNOWN", C_WARNING),
    };

    let title = Line::from(vec![
        Span::styled("  ◈ ", Style::default().fg(C_PRIMARY).add_modifier(Modifier::BOLD)),
        Span::styled(
            "AGENTIC QUANT SANDBOX",
            Style::default().fg(C_PRIMARY).add_modifier(Modifier::BOLD),
        ),
        Span::styled("  │  ", Style::default().fg(C_TEXT_MUTED)),
        Span::styled(&app.clock, Style::default().fg(C_TEXT_DIM)),
        Span::styled("  │  BACKEND: ", Style::default().fg(C_TEXT_MUTED)),
        Span::styled(status_label, Style::default().fg(status_color).add_modifier(Modifier::BOLD)),
    ]);

    let header = Paragraph::new(title)
        .block(
            Block::default()
                .borders(Borders::BOTTOM)
                .border_style(Style::default().fg(C_BORDER))
                .border_type(BorderType::Plain)
                .style(Style::default().bg(C_BG_HEADER)),
        )
        .alignment(Alignment::Left);
    f.render_widget(header, area);
}

// ── Sidebar ────────────────────────────────────────────────────────────────

fn render_sidebar(f: &mut Frame, app: &App, area: Rect) {
    let items: Vec<Line> = vec![
        Line::from(Span::styled(
            "  NAV",
            Style::default().fg(C_TEXT_MUTED).add_modifier(Modifier::BOLD),
        )),
        Line::from(""),
        nav_item("[1] Dashboard", app.active_view == View::Dashboard),
        Line::from(""),
        nav_item("[2] Analyze", app.active_view == View::Analyze),
        Line::from(""),
        nav_item("[3] History", app.active_view == View::History),
        Line::from(""),
        Line::from(Span::styled(
            "─────────────────",
            Style::default().fg(C_TEXT_MUTED),
        )),
        Line::from(""),
        Line::from(Span::styled(
            "  [r] Refresh",
            Style::default().fg(C_TEXT_MUTED),
        )),
        Line::from(Span::styled(
            "  [q] Quit",
            Style::default().fg(C_TEXT_MUTED),
        )),
    ];

    let sidebar = Paragraph::new(items)
        .block(
            Block::default()
                .borders(Borders::RIGHT)
                .border_style(Style::default().fg(C_BORDER))
                .style(Style::default().bg(C_BG_PANEL)),
        );
    f.render_widget(sidebar, area);
}

fn nav_item(label: &str, active: bool) -> Line<'static> {
    if active {
        Line::from(Span::styled(
            format!("▶ {}", label),
            Style::default()
                .fg(C_PRIMARY)
                .bg(C_HIGHLIGHT)
                .add_modifier(Modifier::BOLD),
        ))
    } else {
        Line::from(Span::styled(
            format!("  {}", label),
            Style::default().fg(C_TEXT_DIM),
        ))
    }
}

// ── Footer ─────────────────────────────────────────────────────────────────

fn render_footer(f: &mut Frame, app: &App, area: Rect) {
    let status_text = match &app.loading_state {
        LoadingState::Idle => "Ready".to_string(),
        LoadingState::FetchingResearch => "Running Research Agent…".to_string(),
        LoadingState::FetchingCodeGen => "Running CodeGen Agent…".to_string(),
        LoadingState::FetchingCritic => "Running Critic Agent…".to_string(),
        LoadingState::Complete => format!("Analysis complete — {}", app.current_symbol),
        LoadingState::Error(e) => format!("Error: {}", e),
    };

    let footer = Paragraph::new(Line::from(vec![
        Span::styled(
            "  [1/2/3] Switch View  [Enter] Analyze  [r] Refresh  [q] Quit  │  ",
            Style::default().fg(C_TEXT_MUTED),
        ),
        Span::styled(
            &status_text,
            Style::default().fg(match &app.loading_state {
                LoadingState::Error(_) => C_ERROR,
                LoadingState::Complete => C_SUCCESS,
                LoadingState::Idle => C_TEXT_DIM,
                _ => C_WARNING,
            }),
        ),
    ]))
    .style(Style::default().bg(C_BG_HEADER));
    f.render_widget(footer, area);
}

// ── Dashboard ──────────────────────────────────────────────────────────────

fn render_dashboard(f: &mut Frame, app: &mut App, spinner_tick: &Instant, area: Rect) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .margin(1)
        .constraints([
            Constraint::Length(9),  // agent cards
            Constraint::Min(6),     // bottom panels
        ])
        .split(area);

    // Agent cards row
    let card_cols = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Ratio(1, 3),
            Constraint::Ratio(1, 3),
            Constraint::Ratio(1, 3),
        ])
        .split(chunks[0]);

    for (i, agent) in app.agents.iter().enumerate() {
        render_agent_card(f, agent, spinner_tick, card_cols[i]);
    }

    // Bottom panels
    let bottom = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Min(1),
            Constraint::Length(32),
        ])
        .split(chunks[1]);

    render_feed_log(f, app, bottom[0]);
    render_system_status(f, app, bottom[1]);
}

fn render_agent_card(f: &mut Frame, agent: &AgentStatus, spinner_tick: &Instant, area: Rect) {
    let spin = if agent.state == AgentState::Running {
        format!(" {}", spinner_frame(spinner_tick))
    } else {
        String::new()
    };

    let content = vec![
        Line::from(Span::styled(
            format!("  {}", agent.name),
            Style::default()
                .fg(C_PRIMARY)
                .add_modifier(Modifier::BOLD),
        )),
        Line::from(""),
        Line::from(Span::styled(
            format!("  {}{}", agent.state_label(), spin),
            Style::default()
                .fg(agent.state_color())
                .add_modifier(Modifier::BOLD),
        )),
        Line::from(""),
        Line::from(Span::styled(
            format!("  {}", agent.description),
            Style::default().fg(C_TEXT_DIM),
        )),
        Line::from(""),
        Line::from(Span::styled(
            format!("  Last: {}", agent.last_activity),
            Style::default().fg(C_TEXT_MUTED),
        )),
    ];

    let border_color = match agent.state {
        AgentState::Running => C_WARNING,
        AgentState::Done => C_SUCCESS,
        AgentState::Error => C_ERROR,
        AgentState::Idle => C_BORDER,
    };

    let card = Paragraph::new(content)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_style(Style::default().fg(border_color))
                .border_type(BorderType::Rounded)
                .style(Style::default().bg(C_BG_PANEL)),
        );
    f.render_widget(card, area);
}

fn render_feed_log(f: &mut Frame, app: &App, area: Rect) {
    let items: Vec<ListItem> = app
        .feed_log
        .iter()
        .rev()
        .map(|line| {
            let style = if line.contains('✓') {
                Style::default().fg(C_SUCCESS)
            } else if line.contains('✗') {
                Style::default().fg(C_ERROR)
            } else {
                Style::default().fg(C_TEXT_DIM)
            };
            ListItem::new(Line::from(Span::styled(format!("  {}", line), style)))
        })
        .collect();

    let list = List::new(items)
        .block(
            Block::default()
                .title(Span::styled(
                    "  ▸ RECENT ANALYSES",
                    Style::default().fg(C_PRIMARY).add_modifier(Modifier::BOLD),
                ))
                .borders(Borders::ALL)
                .border_style(Style::default().fg(C_BORDER))
                .border_type(BorderType::Rounded)
                .style(Style::default().bg(C_BG_PANEL)),
        );
    f.render_widget(list, area);
}

fn render_system_status(f: &mut Frame, app: &App, area: Rect) {
    let (be_label, be_color) = match app.backend_status {
        BackendStatus::Online => ("ONLINE", C_SUCCESS),
        BackendStatus::Offline => ("OFFLINE", C_ERROR),
        BackendStatus::Unknown => ("UNKNOWN", C_WARNING),
    };

    let runs_str = app.history.len().to_string();
    let last_resp = app.last_response_time.as_deref().unwrap_or("—");

    let content = vec![
        status_row("BACKEND", be_label, be_color),
        Line::from(""),
        status_row("LAST PING", last_resp, C_TEXT_DIM),
        Line::from(""),
        status_row("RUNS", &runs_str, C_PRIMARY),
        Line::from(""),
        status_row("URL", "127.0.0.1:8000", C_TEXT_MUTED),
    ];

    let panel = Paragraph::new(content)
        .block(
            Block::default()
                .title(Span::styled(
                    "  ▸ SYSTEM",
                    Style::default().fg(C_PRIMARY).add_modifier(Modifier::BOLD),
                ))
                .borders(Borders::ALL)
                .border_style(Style::default().fg(C_BORDER))
                .border_type(BorderType::Rounded)
                .style(Style::default().bg(C_BG_PANEL)),
        );
    f.render_widget(panel, area);
}

fn status_row<'a>(key: &'a str, val: &'a str, val_color: Color) -> Line<'a> {
    Line::from(vec![
        Span::styled(format!("  {:<9}", key), Style::default().fg(C_TEXT_MUTED)),
        Span::styled(val, Style::default().fg(val_color).add_modifier(Modifier::BOLD)),
    ])
}

// ── Analyze View ───────────────────────────────────────────────────────────

fn render_analyze(f: &mut Frame, app: &mut App, spinner_tick: &Instant, area: Rect) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .margin(1)
        .constraints([
            Constraint::Length(5),  // input bar
            Constraint::Min(1),     // pipeline panels
        ])
        .split(area);

    render_ticker_input(f, app, chunks[0]);
    render_pipeline(f, app, spinner_tick, chunks[1]);
}

fn render_ticker_input(f: &mut Frame, app: &App, area: Rect) {
    let running = !matches!(app.loading_state, LoadingState::Idle | LoadingState::Complete | LoadingState::Error(_));
    let placeholder = if app.ticker_input.is_empty() && !running {
        "BTC-USD  ETH-USD  AAPL  TSLA  NVDA …"
    } else {
        ""
    };

    let input_display = if app.ticker_input.is_empty() {
        Span::styled(
            format!("  {}│", placeholder),
            Style::default().fg(C_TEXT_MUTED),
        )
    } else {
        Span::styled(
            format!("  {}", app.input_with_cursor()),
            Style::default().fg(C_PRIMARY).add_modifier(Modifier::BOLD),
        )
    };

    let btn_text = if running {
        format!(" ◉ ANALYZING {}… ", app.current_symbol)
    } else {
        "  ▶  RUN ANALYSIS [Enter]  ".to_string()
    };

    let btn_style = if running {
        Style::default().fg(C_WARNING).add_modifier(Modifier::BOLD)
    } else {
        Style::default().fg(C_PRIMARY).add_modifier(Modifier::BOLD)
    };

    let row = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Min(1),
            Constraint::Length(30),
        ])
        .split(area);

    let input_widget = Paragraph::new(Line::from(input_display))
        .block(
            Block::default()
                .title(Span::styled(
                    "  ◈ TICKER SYMBOL",
                    Style::default().fg(C_TEXT_DIM).add_modifier(Modifier::BOLD),
                ))
                .borders(Borders::ALL)
                .border_style(Style::default().fg(if running { C_WARNING } else { C_PRIMARY }))
                .border_type(BorderType::Rounded)
                .style(Style::default().bg(C_BG_PANEL)),
        );
    f.render_widget(input_widget, row[0]);

    let btn_widget = Paragraph::new(Line::from(Span::styled(btn_text, btn_style)))
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_style(Style::default().fg(if running { C_WARNING } else { C_BORDER }))
                .border_type(BorderType::Rounded)
                .style(Style::default().bg(C_BG_PANEL)),
        )
        .alignment(Alignment::Center);
    f.render_widget(btn_widget, row[1]);
}

fn render_pipeline(f: &mut Frame, app: &mut App, spinner_tick: &Instant, area: Rect) {
    let panels = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Ratio(1, 3),
            Constraint::Ratio(1, 3),
            Constraint::Ratio(1, 3),
        ])
        .split(area);

    render_research_panel(f, app, spinner_tick, panels[0]);
    render_codegen_panel(f, app, spinner_tick, panels[1]);
    render_critic_panel(f, app, spinner_tick, panels[2]);
}

fn render_research_panel(f: &mut Frame, app: &App, spinner_tick: &Instant, area: Rect) {
    let agent = &app.agents[0];
    let spin = if agent.state == AgentState::Running {
        format!(" {}", spinner_frame(spinner_tick))
    } else {
        String::new()
    };

    let badge = format!("{}  {}{}", agent.state_label(), spin, "");
    let border_color = match agent.state {
        AgentState::Running => C_WARNING,
        AgentState::Done => C_PRIMARY,
        AgentState::Error => C_ERROR,
        AgentState::Idle => C_BORDER,
    };

    let content = if app.research_output.is_empty() {
        match agent.state {
            AgentState::Running => vec![
                Line::from(""),
                Line::from(Span::styled(
                    format!("  {} Fetching market data…", spinner_frame(spinner_tick)),
                    Style::default().fg(C_WARNING),
                )),
                Line::from(Span::styled(
                    "  Running AI analysis…",
                    Style::default().fg(C_TEXT_DIM),
                )),
            ],
            AgentState::Idle => vec![
                Line::from(""),
                Line::from(Span::styled(
                    "  Enter a ticker symbol above",
                    Style::default().fg(C_TEXT_MUTED),
                )),
                Line::from(Span::styled(
                    "  and press [Enter] to begin.",
                    Style::default().fg(C_TEXT_MUTED),
                )),
            ],
            _ => vec![Line::from(Span::styled("  No data.", Style::default().fg(C_TEXT_MUTED)))],
        }
    } else {
        app.research_output
            .lines()
            .map(|l| {
                Line::from(Span::styled(
                    format!("  {}", l),
                    Style::default().fg(C_TEXT),
                ))
            })
            .collect()
    };

    let panel = Paragraph::new(content)
        .block(
            Block::default()
                .title(Line::from(vec![
                    Span::styled(
                        "  ◈ RESEARCH AGENT  ",
                        Style::default().fg(C_PRIMARY).add_modifier(Modifier::BOLD),
                    ),
                    Span::styled(badge, Style::default().fg(agent.state_color()).add_modifier(Modifier::BOLD)),
                ]))
                .borders(Borders::ALL)
                .border_style(Style::default().fg(border_color))
                .border_type(BorderType::Rounded)
                .style(Style::default().bg(C_BG_PANEL)),
        )
        .wrap(Wrap { trim: false })
        .scroll((app.research_scroll, 0));
    f.render_widget(panel, area);
}

fn render_codegen_panel(f: &mut Frame, app: &App, spinner_tick: &Instant, area: Rect) {
    let agent = &app.agents[1];
    let spin = if agent.state == AgentState::Running {
        format!(" {}", spinner_frame(spinner_tick))
    } else {
        String::new()
    };
    let badge = format!("{}  {}", agent.state_label(), spin);
    let border_color = match agent.state {
        AgentState::Running => C_WARNING,
        AgentState::Done => C_SECONDARY,
        AgentState::Error => C_ERROR,
        AgentState::Idle => C_BORDER,
    };

    let content: Vec<Line> = if app.codegen_output.is_empty() {
        match agent.state {
            AgentState::Running => vec![
                Line::from(""),
                Line::from(Span::styled(
                    format!("  {} Generating strategy code…", spinner_frame(spinner_tick)),
                    Style::default().fg(C_WARNING),
                )),
            ],
            _ => vec![
                Line::from(""),
                Line::from(Span::styled(
                    "  Awaiting Research Agent…",
                    Style::default().fg(C_TEXT_MUTED),
                )),
            ],
        }
    } else {
        app.codegen_output
            .lines()
            .map(|l| {
                let style = if l.starts_with("def ") || l.starts_with("class ") || l.starts_with("import ") || l.starts_with("from ") {
                    Style::default().fg(C_SECONDARY).add_modifier(Modifier::BOLD)
                } else if l.trim().starts_with('#') {
                    Style::default().fg(C_TEXT_DIM)
                } else {
                    Style::default().fg(C_TEXT)
                };
                Line::from(Span::styled(format!("  {}", l), style))
            })
            .collect()
    };

    let panel = Paragraph::new(content)
        .block(
            Block::default()
                .title(Line::from(vec![
                    Span::styled(
                        "  ◈ CODEGEN AGENT  ",
                        Style::default().fg(C_SECONDARY).add_modifier(Modifier::BOLD),
                    ),
                    Span::styled(badge, Style::default().fg(agent.state_color()).add_modifier(Modifier::BOLD)),
                ]))
                .borders(Borders::ALL)
                .border_style(Style::default().fg(border_color))
                .border_type(BorderType::Rounded)
                .style(Style::default().bg(C_BG_PANEL)),
        )
        .wrap(Wrap { trim: false })
        .scroll((app.codegen_scroll, 0));
    f.render_widget(panel, area);
}

fn render_critic_panel(f: &mut Frame, app: &App, spinner_tick: &Instant, area: Rect) {
    let agent = &app.agents[2];
    let spin = if agent.state == AgentState::Running {
        format!(" {}", spinner_frame(spinner_tick))
    } else {
        String::new()
    };
    let badge = format!("{}  {}", agent.state_label(), spin);

    let verdict = app.critic_output.verdict.as_deref().unwrap_or("—");
    let border_color = match (agent.state.clone(), verdict) {
        (AgentState::Done, "PASS") => C_SUCCESS,
        (AgentState::Done, _) if verdict != "—" => C_ERROR,
        (AgentState::Running, _) => C_WARNING,
        (AgentState::Error, _) => C_ERROR,
        _ => C_BORDER,
    };

    let mut content: Vec<Line> = Vec::new();

    if app.critic_output.verdict.is_none() {
        content.push(Line::from(""));
        match agent.state {
            AgentState::Running => {
                content.push(Line::from(Span::styled(
                    format!("  {} Auditing strategy…", spinner_frame(spinner_tick)),
                    Style::default().fg(C_WARNING),
                )));
            }
            _ => {
                content.push(Line::from(Span::styled(
                    "  Awaiting CodeGen Agent…",
                    Style::default().fg(C_TEXT_MUTED),
                )));
            }
        }
    } else {
        let (v_color, v_icon) = if verdict == "PASS" {
            (C_SUCCESS, "✓")
        } else {
            (C_ERROR, "✗")
        };

        content.push(Line::from(Span::styled(
            format!("  {} VERDICT: {}", v_icon, verdict),
            Style::default().fg(v_color).add_modifier(Modifier::BOLD),
        )));

        if let Some(conf) = app.critic_output.confidence {
            content.push(Line::from(Span::styled(
                format!("  CONFIDENCE: {:.0}%", conf * 100.0),
                Style::default().fg(C_TEXT_DIM),
            )));
        }

        content.push(Line::from(""));
        content.push(Line::from(Span::styled(
            "  ─── ISSUES ───────────────────",
            Style::default().fg(C_TEXT_MUTED),
        )));
        let issues = app.critic_output.issue_strings();
        if issues.is_empty() {
            content.push(Line::from(Span::styled(
                "  None detected.",
                Style::default().fg(C_TEXT_MUTED),
            )));
        } else {
            for (i, issue) in issues.iter().enumerate() {
                content.push(Line::from(Span::styled(
                    format!("  {}. {}", i + 1, issue),
                    Style::default().fg(C_ERROR),
                )));
            }
        }

        content.push(Line::from(""));
        content.push(Line::from(Span::styled(
            "  ─── SUGGESTIONS ─────────────",
            Style::default().fg(C_TEXT_MUTED),
        )));
        let suggestions = app.critic_output.suggestion_strings();
        if suggestions.is_empty() {
            content.push(Line::from(Span::styled(
                "  None.",
                Style::default().fg(C_TEXT_MUTED),
            )));
        } else {
            for (i, s) in suggestions.iter().enumerate() {
                content.push(Line::from(Span::styled(
                    format!("  {}. {}", i + 1, s),
                    Style::default().fg(C_SUCCESS),
                )));
            }
        }
    }

    let panel = Paragraph::new(content)
        .block(
            Block::default()
                .title(Line::from(vec![
                    Span::styled(
                        "  ◈ CRITIC AGENT  ",
                        Style::default().fg(border_color).add_modifier(Modifier::BOLD),
                    ),
                    Span::styled(badge, Style::default().fg(agent.state_color()).add_modifier(Modifier::BOLD)),
                ]))
                .borders(Borders::ALL)
                .border_style(Style::default().fg(border_color))
                .border_type(BorderType::Rounded)
                .style(Style::default().bg(C_BG_PANEL)),
        )
        .wrap(Wrap { trim: false })
        .scroll((app.critic_scroll, 0));
    f.render_widget(panel, area);
}

// ── History View ───────────────────────────────────────────────────────────

fn render_history(f: &mut Frame, app: &mut App, area: Rect) {
    let rows: Vec<Row> = app
        .history
        .iter()
        .rev()
        .map(|entry| {
            let verdict_icon: &str = if entry.verdict == "PASS" {
                "✓ PASS"
            } else if entry.verdict == "FAIL" {
                "✗ FAIL"
            } else {
                entry.verdict.as_str()
            };
            let verdict_style = if entry.verdict == "PASS" {
                Style::default().fg(C_SUCCESS).add_modifier(Modifier::BOLD)
            } else if entry.verdict == "FAIL" {
                Style::default().fg(C_ERROR).add_modifier(Modifier::BOLD)
            } else {
                Style::default().fg(C_WARNING)
            };

            Row::new(vec![
                Cell::from(entry.symbol.clone()).style(Style::default().fg(C_PRIMARY).add_modifier(Modifier::BOLD)),
                Cell::from(entry.regime.clone()).style(Style::default().fg(C_TEXT_DIM)),
                Cell::from(verdict_icon).style(verdict_style),
                Cell::from(entry.confidence.clone()).style(Style::default().fg(C_TEXT_DIM)),
                Cell::from(entry.timestamp.clone()).style(Style::default().fg(C_TEXT_MUTED)),
            ])
            .height(1)
            .style(Style::default().bg(C_BG_PANEL))
        })
        .collect();

    let empty_msg = if rows.is_empty() {
        "  No history yet — run an analysis on the Analyze view first."
    } else {
        ""
    };

    let selected_style = Style::default().bg(C_HIGHLIGHT).fg(C_PRIMARY).add_modifier(Modifier::BOLD);

    let header_cells = ["SYMBOL", "REGIME", "VERDICT", "CONFIDENCE", "TIMESTAMP"]
        .iter()
        .map(|h| {
            Cell::from(*h).style(
                Style::default()
                    .fg(C_PRIMARY)
                    .add_modifier(Modifier::BOLD | Modifier::UNDERLINED),
            )
        });

    let header = Row::new(header_cells)
        .height(1)
        .style(Style::default().bg(C_BG_HEADER));

    let table = Table::new(rows, [
        Constraint::Length(12),
        Constraint::Length(14),
        Constraint::Length(10),
        Constraint::Length(12),
        Constraint::Min(20),
    ])
    .header(header)
    .block(
        Block::default()
            .title(Span::styled(
                "  ▸ ANALYSIS HISTORY",
                Style::default().fg(C_PRIMARY).add_modifier(Modifier::BOLD),
            ))
            .borders(Borders::ALL)
            .border_style(Style::default().fg(C_BORDER))
            .border_type(BorderType::Rounded)
            .style(Style::default().bg(C_BG_PANEL)),
    )
    .highlight_style(selected_style)
    .highlight_symbol("▶ ");

    f.render_stateful_widget(table, area, &mut app.history_table_state);

    if app.history.is_empty() {
        let msg = Paragraph::new(empty_msg).style(Style::default().fg(C_TEXT_MUTED));
        let inner = Rect {
            x: area.x + 3,
            y: area.y + 3,
            width: area.width.saturating_sub(6),
            height: 1,
        };
        f.render_widget(msg, inner);
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// EVENT HANDLING
// ─────────────────────────────────────────────────────────────────────────────

fn handle_key_event(app: &mut App, key: event::KeyEvent) {
    // Global shortcuts
    match key.code {
        KeyCode::Char('q') | KeyCode::Char('Q') => {
            if key.modifiers.contains(KeyModifiers::CONTROL) || app.active_view != View::Analyze {
                app.should_quit = true;
                return;
            }
        }
        KeyCode::Char('1') => {
            app.switch_view(View::Dashboard);
            return;
        }
        KeyCode::Char('2') => {
            app.switch_view(View::Analyze);
            return;
        }
        KeyCode::Char('3') => {
            app.switch_view(View::History);
            return;
        }
        KeyCode::Char('r') | KeyCode::Char('R') => {
            if app.active_view != View::Analyze || app.ticker_input.is_empty() {
                let tx = app.msg_tx.clone();
                tokio::spawn(async move {
                    let ok = check_health().await;
                    let _ = tx.send(AppMessage::HealthCheckResult(ok));
                });
                return;
            }
        }
        _ => {}
    }

    // View-specific handling
    match app.active_view {
        View::Analyze => handle_analyze_keys(app, key),
        View::History => handle_history_keys(app, key),
        View::Dashboard => {}
    }
}

fn handle_analyze_keys(app: &mut App, key: event::KeyEvent) {
    match key.code {
        KeyCode::Char(c) => {
            if !key.modifiers.contains(KeyModifiers::CONTROL)
                && !key.modifiers.contains(KeyModifiers::ALT) {
                app.input_push(c);
            }
        }
        KeyCode::Backspace => app.input_backspace(),
        KeyCode::Delete => app.input_delete(),
        KeyCode::Left => app.cursor_left(),
        KeyCode::Right => app.cursor_right(),
        KeyCode::Home => app.input_cursor_position = 0,
        KeyCode::End => app.input_cursor_position = app.ticker_input.chars().count(),
        KeyCode::Enter => {
            let running = !matches!(
                app.loading_state,
                LoadingState::Idle | LoadingState::Complete | LoadingState::Error(_)
            );
            if !running {
                app.run_analysis();
            }
        }
        KeyCode::Up => app.research_scroll = app.research_scroll.saturating_sub(1),
        KeyCode::Down => app.research_scroll = app.research_scroll.saturating_add(1),
        _ => {}
    }
}

fn handle_history_keys(app: &mut App, key: event::KeyEvent) {
    match key.code {
        KeyCode::Down | KeyCode::Char('j') => app.history_next(),
        KeyCode::Up | KeyCode::Char('k') => app.history_prev(),
        _ => {}
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// MAIN — Application entry point and run loop
// ─────────────────────────────────────────────────────────────────────────────

#[tokio::main]
async fn main() -> Result<()> {
    // Set up terminal
    enable_raw_mode().context("failed to enable raw mode")?;
    let mut stdout = io::stdout();
    execute!(stdout, EnterAlternateScreen, EnableMouseCapture)
        .context("failed to enter alternate screen")?;
    let backend = CrosstermBackend::new(stdout);
    let mut terminal = Terminal::new(backend).context("failed to create terminal")?;
    terminal.clear()?;

    // Async message channel
    let (msg_tx, mut msg_rx) = mpsc::unbounded_channel::<AppMessage>();

    // App state
    let mut app = App::new(msg_tx.clone());

    // Background: health check loop
    {
        let tx = msg_tx.clone();
        tokio::spawn(async move {
            loop {
                let ok = check_health().await;
                let _ = tx.send(AppMessage::HealthCheckResult(ok));
                tokio::time::sleep(Duration::from_millis(HEALTH_CHECK_INTERVAL_MS)).await;
            }
        });
    }

    // Background: clock tick loop
    {
        let tx = msg_tx.clone();
        tokio::spawn(async move {
            loop {
                tokio::time::sleep(Duration::from_secs(1)).await;
                let _ = tx.send(AppMessage::ClockTick);
            }
        });
    }

    let spinner_tick = Instant::now();
    let tick_rate = Duration::from_millis(TICK_RATE_MS);
    let mut last_tick = Instant::now();

    // Main render loop
    loop {
        // Drain all pending async messages
        loop {
            match msg_rx.try_recv() {
                Ok(msg) => app.apply_message(msg),
                Err(_) => break,
            }
        }

        // Draw
        terminal.draw(|f| render(f, &mut app, &spinner_tick))?;

        // Event polling with timeout for smooth rendering
        let timeout = tick_rate
            .checked_sub(last_tick.elapsed())
            .unwrap_or(Duration::ZERO);

        if event::poll(timeout).context("event poll failed")? {
            if let Event::Key(key) = event::read().context("event read failed")? {
                // Only handle actual key presses — ignore Release and Repeat
                // to prevent duplicate processing on Windows terminals.
                if key.kind == KeyEventKind::Press {
                    handle_key_event(&mut app, key);
                }
            }
        }

        if last_tick.elapsed() >= tick_rate {
            last_tick = Instant::now();
        }

        if app.should_quit {
            break;
        }
    }

    // Restore terminal
    disable_raw_mode().context("failed to disable raw mode")?;
    execute!(
        terminal.backend_mut(),
        LeaveAlternateScreen,
        DisableMouseCapture
    )
    .context("failed to leave alternate screen")?;
    terminal.show_cursor()?;

    Ok(())
}
