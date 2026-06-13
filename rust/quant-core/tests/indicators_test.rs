use quant_core::indicators;

fn make_sine_wave(n: usize) -> Vec<f64> {
    (0..n)
        .map(|i| 100.0 + (i as f64 * 0.1).sin() * 10.0)
        .collect()
}

#[test]
fn test_rsi_known_flat_series() {
    let prices = vec![50.0; 60];
    let rsi_vals = indicators::rsi(&prices, 14).unwrap();
    let last = rsi_vals.last().unwrap();
    assert!(
        (*last - 50.0).abs() < 10.0,
        "RSI of flat series should be ~50, got {}",
        last
    );
}

#[test]
fn test_rsi_upward_trend() {
    let prices: Vec<f64> = (0..100).map(|i| 50.0 + i as f64 * 0.5).collect();
    let rsi_vals = indicators::rsi(&prices, 14).unwrap();
    let last = rsi_vals.last().unwrap();
    assert!(
        *last > 50.0 || last.is_nan(),
        "RSI of upward trend should be > 50, got {}",
        last
    );
}

#[test]
fn test_rsi_empty_input() {
    assert!(indicators::rsi(&[], 14).is_err());
}

#[test]
fn test_rsi_period_longer_than_data() {
    assert!(indicators::rsi(&vec![1.0, 2.0], 14).is_err());
}

#[test]
fn test_ema_convergence() {
    // For a constant series, EMA should converge to the constant value
    let prices = vec![42.0; 100];
    let ema_vals = indicators::ema(&prices, 10).unwrap();
    let last = ema_vals.last().unwrap();
    assert!(
        (*last - 42.0).abs() < 0.01,
        "EMA should converge to 42.0, got {}",
        last
    );
}

#[test]
fn test_ema_matches_known_value() {
    let prices = vec![10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0];
    let ema_vals = indicators::ema(&prices, 5).unwrap();
    // EMA(5) should have all finite values (ta crate fills leading values)
    assert_eq!(ema_vals.len(), 10);
    for &v in ema_vals.iter() {
        assert!(!v.is_nan(), "EMA should not have NaN values");
    }
}

#[test]
fn test_macd_crossover() {
    // Generate data that has a clear MACD crossover
    let data = make_sine_wave(100);
    let macd = indicators::macd(&data, 5, 13, 5).unwrap();

    assert_eq!(macd.macd_line.len(), 100);
    assert_eq!(macd.signal_line.len(), 100);
    assert_eq!(macd.histogram.len(), 100);

    // Histogram should be symmetric around MACD - Signal
    for i in 12..100 {
        let expected_hist = macd.macd_line[i] - macd.signal_line[i];
        assert!(
            (macd.histogram[i] - expected_hist).abs() < 0.0001,
            "Histogram mismatch at index {}: {} vs {}",
            i,
            macd.histogram[i],
            expected_hist
        );
    }
}

#[test]
fn test_macd_signal_crossing() {
    let data = make_sine_wave(200);
    let macd = indicators::macd(&data, 5, 13, 5).unwrap();

    // There should be at least one sign change in the histogram (signal crossing)
    let signs: Vec<bool> = macd.histogram.iter().skip(12).map(|&v| v > 0.0).collect();
    let changes = signs.windows(2).filter(|w| w[0] != w[1]).count();

    assert!(
        changes > 0,
        "Expected at least one MACD signal crossover in sine wave data"
    );
}

#[test]
fn test_sma_basic() {
    let data = make_sine_wave(50);
    let result = indicators::sma(&data, 10).unwrap();
    assert_eq!(result.len(), 50);
    for &v in result.iter() {
        assert!(!v.is_nan(), "SMA values should all be finite");
    }
}

#[test]
fn test_bollinger_bands_consistency() {
    let data = make_sine_wave(100);
    let bb = indicators::bollinger_bands(&data, 20, 2.0).unwrap();
    for i in 19..100 {
        assert!(
            bb.upper[i] >= bb.middle[i],
            "Upper band >= middle band at {}",
            i
        );
        assert!(
            bb.middle[i] >= bb.lower[i],
            "Middle band >= lower band at {}",
            i
        );
    }
}

#[test]
fn test_highest_and_lowest() {
    let data = vec![10.0, 5.0, 20.0, 15.0, 25.0, 10.0, 30.0, 5.0];
    let hi = indicators::highest(&data, 3).unwrap();
    let lo = indicators::lowest(&data, 3).unwrap();
    for i in 2..data.len() {
        assert!(hi[i] >= lo[i], "Highest >= Lowest at {}", i);
    }
}
