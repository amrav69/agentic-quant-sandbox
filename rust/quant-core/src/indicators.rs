use ta::indicators::{BollingerBands as TaBollingerBands, ExponentialMovingAverage as TaEma, Maximum, Minimum, MovingAverageConvergenceDivergence as TaMacd, RelativeStrengthIndex as TaRsi, SimpleMovingAverage as TaSma};
use ta::DataItem;
use ta::Next;

use crate::error::QuantError;

pub fn sma(data: &[f64], period: usize) -> Result<Vec<f64>, QuantError> {
    if data.is_empty() {
        return Err(QuantError::EmptyInput);
    }
    if period == 0 || period > data.len() {
        return Err(QuantError::InsufficientData {
            required: period,
            available: data.len(),
        });
    }
    let mut indicator = TaSma::new(period).map_err(|e| QuantError::Internal(e.to_string()))?;
    let mut result = Vec::with_capacity(data.len());
    for &v in data {
        let item = DataItem::builder().close(v).open(v).high(v).low(v).volume(0.0).build().map_err(|e| QuantError::Internal(e.to_string()))?;
        let out = indicator.next(&item);
        result.push(out);
    }
    Ok(result)
}

pub fn ema(data: &[f64], period: usize) -> Result<Vec<f64>, QuantError> {
    if data.is_empty() {
        return Err(QuantError::EmptyInput);
    }
    if period == 0 || period > data.len() {
        return Err(QuantError::InsufficientData {
            required: period,
            available: data.len(),
        });
    }
    let mut indicator = TaEma::new(period).map_err(|e| QuantError::Internal(e.to_string()))?;
    let mut result = Vec::with_capacity(data.len());
    for &v in data {
        let item = DataItem::builder().close(v).open(v).high(v).low(v).volume(0.0).build().map_err(|e| QuantError::Internal(e.to_string()))?;
        let out = indicator.next(&item);
        result.push(out);
    }
    Ok(result)
}

pub fn rsi(data: &[f64], period: usize) -> Result<Vec<f64>, QuantError> {
    if data.is_empty() {
        return Err(QuantError::EmptyInput);
    }
    if period == 0 || period > data.len() {
        return Err(QuantError::InsufficientData {
            required: period,
            available: data.len(),
        });
    }
    let mut indicator = TaRsi::new(period).map_err(|e| QuantError::Internal(e.to_string()))?;
    let mut result = Vec::with_capacity(data.len());
    for &v in data {
        let item = DataItem::builder().close(v).open(v).high(v).low(v).volume(0.0).build().map_err(|e| QuantError::Internal(e.to_string()))?;
        let out = indicator.next(&item);
        result.push(out);
    }
    Ok(result)
}

pub struct MacdOutput {
    pub macd_line: Vec<f64>,
    pub signal_line: Vec<f64>,
    pub histogram: Vec<f64>,
}

pub fn macd(data: &[f64], fast: usize, slow: usize, signal: usize) -> Result<MacdOutput, QuantError> {
    if data.is_empty() {
        return Err(QuantError::EmptyInput);
    }
    if slow > data.len() {
        return Err(QuantError::InsufficientData {
            required: slow,
            available: data.len(),
        });
    }
    let mut indicator = TaMacd::new(fast, slow, signal).map_err(|e| QuantError::Internal(e.to_string()))?;
    let mut macd_line = Vec::with_capacity(data.len());
    let mut signal_line = Vec::with_capacity(data.len());
    let mut histogram = Vec::with_capacity(data.len());
    for &v in data {
        let item = DataItem::builder().close(v).open(v).high(v).low(v).volume(0.0).build().map_err(|e| QuantError::Internal(e.to_string()))?;
        let out = indicator.next(&item);
        macd_line.push(out.macd);
        signal_line.push(out.signal);
        histogram.push(out.histogram);
    }
    Ok(MacdOutput { macd_line, signal_line, histogram })
}

pub struct BollingerOutput {
    pub upper: Vec<f64>,
    pub middle: Vec<f64>,
    pub lower: Vec<f64>,
}

pub fn bollinger_bands(data: &[f64], period: usize, std_dev: f64) -> Result<BollingerOutput, QuantError> {
    if data.is_empty() {
        return Err(QuantError::EmptyInput);
    }
    if period == 0 || period > data.len() {
        return Err(QuantError::InsufficientData {
            required: period,
            available: data.len(),
        });
    }
    let mut indicator = TaBollingerBands::new(period, std_dev).map_err(|e| QuantError::Internal(e.to_string()))?;
    let mut upper = Vec::with_capacity(data.len());
    let mut middle = Vec::with_capacity(data.len());
    let mut lower = Vec::with_capacity(data.len());
    for &v in data {
        let item = DataItem::builder().close(v).open(v).high(v).low(v).volume(0.0).build().map_err(|e| QuantError::Internal(e.to_string()))?;
        let out = indicator.next(&item);
        upper.push(out.upper);
        middle.push(out.average);
        lower.push(out.lower);
    }
    Ok(BollingerOutput { upper, middle, lower })
}

pub fn highest(data: &[f64], period: usize) -> Result<Vec<f64>, QuantError> {
    if data.is_empty() {
        return Err(QuantError::EmptyInput);
    }
    if period == 0 || period > data.len() {
        return Err(QuantError::InsufficientData {
            required: period,
            available: data.len(),
        });
    }
    let mut indicator = Maximum::new(period).map_err(|e| QuantError::Internal(e.to_string()))?;
    let mut result = Vec::with_capacity(data.len());
    for &v in data {
        let item = DataItem::builder().close(v).open(v).high(v).low(v).volume(0.0).build().map_err(|e| QuantError::Internal(e.to_string()))?;
        result.push(indicator.next(&item));
    }
    Ok(result)
}

pub fn lowest(data: &[f64], period: usize) -> Result<Vec<f64>, QuantError> {
    if data.is_empty() {
        return Err(QuantError::EmptyInput);
    }
    if period == 0 || period > data.len() {
        return Err(QuantError::InsufficientData {
            required: period,
            available: data.len(),
        });
    }
    let mut indicator = Minimum::new(period).map_err(|e| QuantError::Internal(e.to_string()))?;
    let mut result = Vec::with_capacity(data.len());
    for &v in data {
        let item = DataItem::builder().close(v).open(v).high(v).low(v).volume(0.0).build().map_err(|e| QuantError::Internal(e.to_string()))?;
        result.push(indicator.next(&item));
    }
    Ok(result)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_data(n: usize, base: f64) -> Vec<f64> {
        (0..n).map(|i| base + (i as f64 * 0.5) + (i as f64).sin()).collect()
    }

    #[test]
    fn test_sma_empty() {
        assert!(sma(&[], 14).is_err());
    }

    #[test]
    fn test_sma_insufficient() {
        assert!(sma(&vec![1.0, 2.0], 14).is_err());
    }

    #[test]
    fn test_sma_basic() {
        let data = make_data(100, 100.0);
        let result = sma(&data, 14).unwrap();
        assert_eq!(result.len(), 100);
        for &v in result.iter() {
            assert!(!v.is_nan(), "SMA value should not be NaN");
        }
    }

    #[test]
    fn test_sma_known_values() {
        let data = vec![10.0, 20.0, 30.0, 40.0, 50.0];
        let result = sma(&data, 3).unwrap();
        assert!((result[2] - 20.0).abs() < 1e-10);
        assert!((result[3] - 30.0).abs() < 1e-10);
        assert!((result[4] - 40.0).abs() < 1e-10);
    }

    #[test]
    fn test_ema_basic() {
        let data = make_data(100, 100.0);
        let result = ema(&data, 14).unwrap();
        assert_eq!(result.len(), 100);
    }

    #[test]
    fn test_ema_convergence_to_mean() {
        let data = vec![42.0; 100];
        let result = ema(&data, 10).unwrap();
        let last = result.last().unwrap();
        assert!((*last - 42.0).abs() < 0.01);
    }

    #[test]
    fn test_rsi_known_values() {
        let data = vec![50.0; 30];
        let result = rsi(&data, 14).unwrap();
        let last = result.last().unwrap();
        assert!((*last - 50.0).abs() < 0.1 || last.is_nan());
    }

    #[test]
    fn test_rsi_always_rising() {
        let data: Vec<f64> = (0..100).map(|i| 100.0 + i as f64).collect();
        let result = rsi(&data, 14).unwrap();
        let last = result.last().unwrap();
        assert!(*last > 90.0 || last.is_nan());
    }

    #[test]
    fn test_rsi_always_falling() {
        let data: Vec<f64> = (0..100).map(|i| 500.0 - i as f64).collect();
        let result = rsi(&data, 14).unwrap();
        let last = result.last().unwrap();
        assert!(*last < 10.0 || last.is_nan());
    }

    #[test]
    fn test_rsi_exact_boundaries() {
        let up: Vec<f64> = (0..100).map(|i| 100.0 + i as f64).collect();
        let result_up = rsi(&up, 14).unwrap();
        let last_up = result_up.last().unwrap();
        assert!(*last_up > 90.0);

        let down: Vec<f64> = (0..100).map(|i| 500.0 - i as f64).collect();
        let result_down = rsi(&down, 14).unwrap();
        let last_down = result_down.last().unwrap();
        assert!(*last_down < 10.0);
    }

    #[test]
    fn test_rsi_period_equals_length() {
        let data = make_data(14, 100.0);
        let result = rsi(&data, 14).unwrap();
        assert_eq!(result.len(), 14);
    }

    #[test]
    fn test_macd_crossover_detection() {
        let mut data: Vec<f64> = (0..30).map(|i| 100.0 + i as f64 * 2.0).collect();
        data.extend((0..30).rev().map(|i| 160.0 - i as f64 * 2.0));
        let result = macd(&data, 5, 13, 5).unwrap();
        assert_eq!(result.macd_line.len(), data.len());
        assert_eq!(result.signal_line.len(), data.len());
        assert_eq!(result.histogram.len(), data.len());
    }

    #[test]
    fn test_macd_fast_slow_signal_values() {
        let data = make_data(50, 100.0);
        let result = macd(&data, 5, 13, 5).unwrap();
        for i in 12..50 {
            let expected_hist = result.macd_line[i] - result.signal_line[i];
            assert!((result.histogram[i] - expected_hist).abs() < 1e-10);
        }
    }

    #[test]
    fn test_macd_slow_exceeds_length() {
        let data = make_data(10, 100.0);
        assert!(macd(&data, 5, 13, 5).is_err());
    }

    #[test]
    fn test_bollinger_bands_shape() {
        let data = make_data(100, 100.0);
        let bb = bollinger_bands(&data, 20, 2.0).unwrap();
        assert_eq!(bb.upper.len(), 100);
        assert_eq!(bb.middle.len(), 100);
        assert_eq!(bb.lower.len(), 100);
        for i in 19..100 {
            assert!(
                bb.upper[i] >= bb.lower[i],
                "upper[{i}]={} < lower[{i}]={}",
                bb.upper[i],
                bb.lower[i]
            );
        }
    }

    #[test]
    fn test_bollinger_bands_zero_stddev() {
        let data = vec![100.0; 50];
        let bb = bollinger_bands(&data, 20, 0.0).unwrap();
        for i in 19..50 {
            assert!((bb.upper[i] - bb.middle[i]).abs() < 1e-10);
            assert!((bb.middle[i] - bb.lower[i]).abs() < 1e-10);
        }
    }

    #[test]
    fn test_bollinger_bands_middle_is_sma() {
        let data = make_data(50, 100.0);
        let bb = bollinger_bands(&data, 20, 2.0).unwrap();
        let sma_vals = sma(&data, 20).unwrap();
        for i in 19..50 {
            assert!((bb.middle[i] - sma_vals[i]).abs() < 1e-10);
        }
    }

    #[test]
    fn test_bollinger_bands_period_equals_length() {
        let data = make_data(20, 100.0);
        let result = bollinger_bands(&data, 20, 2.0).unwrap();
        assert_eq!(result.upper.len(), 20);
    }

    #[test]
    fn test_highest_lowest() {
        let data = vec![3.0, 1.0, 4.0, 1.0, 5.0, 9.0, 2.0, 6.0];
        let hi = highest(&data, 3).unwrap();
        let lo = lowest(&data, 3).unwrap();
        assert_eq!(hi.len(), 8);
        assert_eq!(lo.len(), 8);
        for i in 2..data.len() {
            assert!(hi[i] >= lo[i]);
        }
    }

    #[test]
    fn test_highest_known_values() {
        let data = vec![1.0, 5.0, 3.0, 8.0, 2.0, 9.0, 4.0];
        let result = highest(&data, 3).unwrap();
        assert!((result[2] - 5.0).abs() < 1e-10);
        assert!((result[3] - 8.0).abs() < 1e-10);
        assert!((result[4] - 8.0).abs() < 1e-10);
    }

    #[test]
    fn test_lowest_known_values() {
        let data = vec![5.0, 3.0, 8.0, 1.0, 7.0, 2.0];
        let result = lowest(&data, 3).unwrap();
        assert!((result[2] - 3.0).abs() < 1e-10);
        assert!((result[3] - 1.0).abs() < 1e-10);
        assert!((result[4] - 1.0).abs() < 1e-10);
    }

    #[test]
    fn test_zero_period() {
        let data = make_data(100, 100.0);
        assert!(sma(&data, 0).is_err());
        assert!(ema(&data, 0).is_err());
        assert!(rsi(&data, 0).is_err());
        assert!(bollinger_bands(&data, 0, 2.0).is_err());
        assert!(highest(&data, 0).is_err());
        assert!(lowest(&data, 0).is_err());
    }

    #[test]
    fn test_single_element() {
        assert!(sma(&vec![1.0], 1).is_ok());
        assert!(rsi(&vec![1.0], 1).is_ok());
        assert!(ema(&vec![1.0], 1).is_ok());
    }

    #[test]
    fn test_all_indicators_return_correct_length() {
        let data = make_data(100, 100.0);
        assert_eq!(sma(&data, 14).unwrap().len(), 100);
        assert_eq!(ema(&data, 14).unwrap().len(), 100);
        assert_eq!(rsi(&data, 14).unwrap().len(), 100);
        let bb = bollinger_bands(&data, 20, 2.0).unwrap();
        assert_eq!(bb.upper.len(), 100);
        assert_eq!(bb.lower.len(), 100);
        let macd = macd(&data, 5, 13, 5).unwrap();
        assert_eq!(macd.macd_line.len(), 100);
    }
}
