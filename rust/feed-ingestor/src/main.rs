use clap::Parser;
use futures_util::{SinkExt, StreamExt};
use serde::Serialize;
use tokio::signal;
use tracing_subscriber::EnvFilter;

#[derive(Debug, Serialize)]
struct Tick {
    symbol: String,
    price: f64,
    volume: f64,
    timestamp: u64,
}

#[derive(Parser, Debug)]
#[command(name = "feed-ingestor", about = "Real-time market data feed ingestor")]
struct Args {
    /// WebSocket URL to connect to
    #[arg(short, long, env = "WS_URL")]
    ws_url: String,

    /// Comma-separated list of symbols to subscribe to
    #[arg(short, long, env = "SYMBOLS")]
    symbols: String,

    /// Dry run: connect, print 5 messages, then exit
    #[arg(long, default_value_t = false)]
    dry_run: bool,

    /// Data provider: polygon or alpaca
    #[arg(long, default_value = "polygon")]
    provider: String,
}

fn build_subscription_message(provider: &str, symbols: &[&str]) -> serde_json::Value {
    match provider {
        "alpaca" => serde_json::json!({
            "action": "subscribe",
            "trades": symbols,
            "quotes": symbols,
            "bars": symbols
        }),
        _ => serde_json::json!({
            "action": "subscribe",
            "params": symbols.join(",")
        }),
    }
}

fn parse_tick(provider: &str, msg: &serde_json::Value) -> Option<Tick> {
    match provider {
        "alpaca" => {
            let arr = msg.get("T").and_then(|v| v.as_array())?;
            let first = arr.first()?;
            Some(Tick {
                symbol: first.get("S")?.as_str()?.to_string(),
                price: first.get("p")?.as_f64()?,
                volume: first.get("s")?.as_f64()?,
                timestamp: first.get("t")?.as_u64().unwrap_or(0),
            })
        }
        _ => {
            // Polygon-style: {"ev": "AM", "sym": "AAPL", "p": 150.0, "s": 100, "t": 1234567890}
            Some(Tick {
                symbol: msg.get("sym")?.as_str()?.to_string(),
                price: msg.get("p")?.as_f64()?,
                volume: msg.get("s")?.as_f64().unwrap_or(0.0),
                timestamp: msg.get("t")?.as_u64().unwrap_or(0),
            })
        }
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::from_default_env())
        .with_target(false)
        .init();

    let args = Args::parse();
    let symbols: Vec<&str> = args.symbols.split(',').map(|s| s.trim()).collect();
    let ws_url = if args.provider == "polygon" && !args.ws_url.contains("stocks") {
        format!("{}/stocks", args.ws_url.trim_end_matches('/'))
    } else {
        args.ws_url.clone()
    };

    tracing::info!(
        "Connecting to {} as {} provider for symbols: {:?}",
        ws_url,
        args.provider,
        symbols
    );

    let (ws_stream, _response) = tokio_tungstenite::connect_async(&ws_url).await?;
    tracing::info!("WebSocket connected");

    let (mut write, mut read) = ws_stream.split();

    // Subscribe to symbols
    let sub_msg = build_subscription_message(&args.provider, &symbols);
    let sub_text = serde_json::to_string(&sub_msg)?;
    write.send(tokio_tungstenite::tungstenite::Message::Text(sub_text)).await?;
    tracing::info!("Subscription sent for {:?}", symbols);

    let mut msg_count = 0u64;
    let max_msgs = if args.dry_run { 5u64 } else { u64::MAX };

    let ctrl_c = signal::ctrl_c();
    tokio::pin!(ctrl_c);

    while msg_count < max_msgs {
        tokio::select! {
            msg = read.next() => {
                match msg {
                    Some(Ok(tokio_tungstenite::tungstenite::Message::Text(text))) => {
                        if let Ok(json_val) = serde_json::from_str::<serde_json::Value>(&text) {
                            if let Some(tick) = parse_tick(&args.provider, &json_val) {
                                let output = serde_json::to_string(&tick)?;
                                println!("{}", output);
                                msg_count += 1;
                            }
                        }
                    }
                    Some(Ok(tokio_tungstenite::tungstenite::Message::Close(_))) => {
                        tracing::info!("WebSocket closed by server");
                        break;
                    }
                    Some(Err(e)) => {
                        tracing::error!("WebSocket error: {}", e);
                        break;
                    }
                    None => {
                        tracing::info!("WebSocket stream ended");
                        break;
                    }
                    _ => {}
                }
            }
            _ = &mut ctrl_c => {
                tracing::info!("Ctrl-C received, shutting down");
                break;
            }
        }
    }

    if args.dry_run {
        tracing::info!("Dry run complete. Processed {} messages.", msg_count);
    } else {
        tracing::info!("Feed ingestor shutting down after {} messages.", msg_count);
    }

    Ok(())
}
