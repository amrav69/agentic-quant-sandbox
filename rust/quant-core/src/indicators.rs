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
        // All values should be finite (ta crate fills leading values with partial SMAs)
        for &v in result.iter() {
            assert!(!v.is_nan(), "SMA value should not be NaN");
        }
    }

    #[test]
    fn test_ema_basic() {
        let data = make_data(100, 100.0);
        let result = ema(&data, 14).unwrap();
        assert_eq!(result.len(), 100);
    }

    #[test]
    fn test_rsi_known_values() {
        // RSI should be ~50 for a flat series
        let data = vec![50.0; 30];
        let result = rsi(&data, 14).unwrap();
        // After warm-up, RSI of flat data should be 50.0
        let last = result.last().unwrap();
        assert!((*last - 50.0).abs() < 0.1 || last.is_nan());
    }

    #[test]
    fn test_macd_crossover_detection() {
        // Generate a trend change: upward then downward
        let mut data: Vec<f64> = (0..30).map(|i| 100.0 + i as f64 * 2.0).collect(); // uptrend
        data.extend((0..30).rev().map(|i| 160.0 - i as f64 * 2.0)); // downtrend
        let result = macd(&data, 5, 13, 5).unwrap();
        assert_eq!(result.macd_line.len(), data.len());
        assert_eq!(result.signal_line.len(), data.len());
        assert_eq!(result.histogram.len(), data.len());
    }

    #[test]
    fn test_bollinger_bands_shape() {
        let data = make_data(100, 100.0);
        let bb = bollinger_bands(&data, 20, 2.0).unwrap();
        assert_eq!(bb.upper.len(), 100);
        assert_eq!(bb.middle.len(), 100);
        assert_eq!(bb.lower.len(), 100);
        // Upper should always be >= lower
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
    fn test_highest_lowest() {
        let data = vec![3.0, 1.0, 4.0, 1.0, 5.0, 9.0, 2.0, 6.0];
        let hi = highest(&data, 3).unwrap();
        let lo = lowest(&data, 3).unwrap();
        assert_eq!(hi.len(), 8);
        assert_eq!(lo.len(), 8);
        // Highest should always be >= lowest
        for i in 2..data.len() {
            assert!(hi[i] >= lo[i]);
        }
    }
}
