use proptest::prelude::*;

// Value strategy that avoids degenerate inputs (all-zeros, etc.) that
// cause the underlying `ta` crate to error out internally.
fn positive_data() -> impl Strategy<Value = Vec<f64>> {
    prop::collection::vec(0.01f64..1_000_000.0, 1..200)
}

proptest! {
    #[test]
    fn sma_never_panics(data in positive_data(), period in 1usize..50) {
        if period <= data.len() {
            let result = quant_core::indicators::sma(&data, period);
            prop_assert!(result.is_ok());
            if let Ok(v) = result {
                prop_assert_eq!(v.len(), data.len());
            }
        }
    }

    #[test]
    fn ema_never_panics(data in positive_data(), period in 1usize..50) {
        if period <= data.len() {
            let result = quant_core::indicators::ema(&data, period);
            prop_assert!(result.is_ok());
            if let Ok(v) = result {
                prop_assert_eq!(v.len(), data.len());
            }
        }
    }

    #[test]
    fn rsi_range(data in prop::collection::vec(0.01f64..10000.0, 15..200)) {
        let result = quant_core::indicators::rsi(&data, 14);
        prop_assert!(result.is_ok());
        if let Ok(v) = result {
            for &val in v.iter().skip(14) {
                prop_assert!((0.0..=100.0).contains(&val) || val.is_nan());
            }
        }
    }

    #[test]
    fn bollinger_upper_gte_lower(data in positive_data().prop_filter("need at least 21 positive values", |v| v.iter().filter(|&&x| x > 0.0).count() >= 21)) {
        let result = quant_core::indicators::bollinger_bands(&data, 20, 2.0);
        if let Ok(bb) = result {
            for i in 19..data.len() {
                prop_assert!(bb.upper[i] >= bb.lower[i], "upper={} < lower={} at {i}", bb.upper[i], bb.lower[i]);
            }
        }
    }

    #[test]
    fn macd_histogram_consistency(data in positive_data().prop_filter("need at least 30 positive values", |v| v.iter().filter(|&&x| x > 0.0).count() >= 30)) {
        let result = quant_core::indicators::macd(&data, 5, 13, 5);
        if let Ok(macd) = result {
            for i in 12..data.len() {
                let expected = macd.macd_line[i] - macd.signal_line[i];
                prop_assert!((macd.histogram[i] - expected).abs() < 1e-8,
                    "hist mismatch at {i}: {} vs {expected}", macd.histogram[i]);
            }
        }
    }

    #[test]
    fn highest_lowest_bounds(data in prop::collection::vec(-1e6f64..1e6, 10..200)) {
        for period in [3usize, 5, 10, 14, 20] {
            if let (Ok(hi), Ok(lo)) = (
                quant_core::indicators::highest(&data, period),
                quant_core::indicators::lowest(&data, period),
            ) {
                for i in (period - 1)..data.len() {
                    prop_assert!(hi[i] >= lo[i], "highest < lowest at index {i}");
                }
            }
        }
    }

    #[test]
    fn zero_period_returns_error(data in prop::collection::vec(1.0f64..100.0, 1..50)) {
        prop_assert!(quant_core::indicators::sma(&data, 0).is_err());
        prop_assert!(quant_core::indicators::ema(&data, 0).is_err());
        prop_assert!(quant_core::indicators::rsi(&data, 0).is_err());
        prop_assert!(quant_core::indicators::bollinger_bands(&data, 0, 2.0).is_err());
        prop_assert!(quant_core::indicators::highest(&data, 0).is_err());
        prop_assert!(quant_core::indicators::lowest(&data, 0).is_err());
    }
}
