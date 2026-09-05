pub mod error;
pub mod indicators;

use error::QuantError;

/// Pure Rust RSI calculation. Takes a slice of prices and a period,
/// returns a Vec of RSI values (same length as input, leading values are NaN).
pub fn calculate_rsi(prices: &[f64], period: usize) -> Result<Vec<f64>, QuantError> {
    indicators::rsi(prices, period)
}

/// Pure Rust SMA calculation.
pub fn calculate_sma(prices: &[f64], period: usize) -> Result<Vec<f64>, QuantError> {
    indicators::sma(prices, period)
}

/// Pure Rust EMA calculation.
pub fn calculate_ema(prices: &[f64], period: usize) -> Result<Vec<f64>, QuantError> {
    indicators::ema(prices, period)
}

/// Pure Rust ATR calculation over high/low/close series.
/// Returns a Vec of the same length; the first `period - 1` values are NaN.
pub fn calculate_atr(
    high: &[f64],
    low: &[f64],
    close: &[f64],
    period: usize,
) -> Result<Vec<f64>, QuantError> {
    indicators::atr(high, low, close, period)
}

/// Pure Rust MACD calculation.
pub fn calculate_macd(
    prices: &[f64],
    fast: usize,
    slow: usize,
    signal: usize,
) -> Result<indicators::MacdOutput, QuantError> {
    indicators::macd(prices, fast, slow, signal)
}

/// Pure Rust Bollinger Bands calculation.
pub fn calculate_bollinger(
    prices: &[f64],
    period: usize,
    std_dev: f64,
) -> Result<indicators::BollingerOutput, QuantError> {
    indicators::bollinger_bands(prices, period, std_dev)
}

extern "C" fn calc_rsi_impl(
    prices: *const f64,
    len: usize,
    period: usize,
    out: *mut f64,
    out_len: *mut usize,
) -> i32 {
    if prices.is_null() || out.is_null() || out_len.is_null() {
        return -1;
    }
    let data = unsafe { std::slice::from_raw_parts(prices, len) };
    let result = match calculate_rsi(data, period) {
        Ok(v) => v,
        Err(_) => return -2,
    };
    let result_len = result.len();
    unsafe {
        std::ptr::write(out_len, result_len);
        for (i, val) in result.iter().enumerate() {
            std::ptr::write(out.add(i), *val);
        }
    }
    0
}

/// FFI-safe RSI calculation for C/Python interop.
/// Returns 0 on success, negative on error.
/// -1: null pointer   -2: calculation error
#[no_mangle]
pub extern "C" fn calc_rsi(
    prices: *const f64,
    len: usize,
    period: usize,
    out: *mut f64,
    out_len: *mut usize,
) -> i32 {
    calc_rsi_impl(prices, len, period, out, out_len)
}

#[cfg(feature = "python")]
pub mod python {
    use crate::{calculate_atr, calculate_ema, calculate_macd, calculate_rsi};
    use pyo3::prelude::*;

    #[pyfunction]
    pub fn calculate_rsi_py(prices: Vec<f64>, period: usize) -> PyResult<Vec<f64>> {
        calculate_rsi(&prices, period)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
    }

    #[pyfunction]
    pub fn calculate_ema_py(prices: Vec<f64>, period: usize) -> PyResult<Vec<f64>> {
        calculate_ema(&prices, period)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
    }

    #[pyfunction]
    pub fn calculate_macd_py(
        prices: Vec<f64>,
        fast: usize,
        slow: usize,
        signal: usize,
    ) -> PyResult<(Vec<f64>, Vec<f64>, Vec<f64>)> {
        let out = calculate_macd(&prices, fast, slow, signal)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
        Ok((out.macd_line, out.signal_line, out.histogram))
    }

    #[pyfunction]
    pub fn calculate_atr_py(
        high: Vec<f64>,
        low: Vec<f64>,
        close: Vec<f64>,
        period: usize,
    ) -> PyResult<Vec<f64>> {
        calculate_atr(&high, &low, &close, period)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
    }

    #[pymodule]
    fn quant_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(calculate_rsi_py, m)?)?;
        m.add_function(wrap_pyfunction!(calculate_ema_py, m)?)?;
        m.add_function(wrap_pyfunction!(calculate_atr_py, m)?)?;
        m.add_function(wrap_pyfunction!(calculate_macd_py, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_data(n: usize) -> Vec<f64> {
        (0..n)
            .map(|i| 100.0 + (i as f64 * 0.5) + (i as f64).sin())
            .collect()
    }

    #[test]
    fn test_calculate_rsi_wrapper() {
        let data = make_data(100);
        let result = calculate_rsi(&data, 14).unwrap();
        assert_eq!(result.len(), 100);
    }

    #[test]
    fn test_calculate_sma_wrapper() {
        let data = make_data(100);
        let result = calculate_sma(&data, 14).unwrap();
        assert_eq!(result.len(), 100);
    }

    #[test]
    fn test_calculate_ema_wrapper() {
        let data = make_data(100);
        let result = calculate_ema(&data, 14).unwrap();
        assert_eq!(result.len(), 100);
    }

    #[test]
    fn test_calculate_atr_wrapper() {
        let n = 100;
        let close = make_data(n);
        let high: Vec<f64> = close.iter().map(|&c| c + 0.75).collect();
        let low: Vec<f64> = close.iter().map(|&c| c - 0.5).collect();
        let result = calculate_atr(&high, &low, &close, 14).unwrap();
        assert_eq!(result.len(), n);
        assert!(result[..13].iter().all(|v| v.is_nan()));
        assert!(result[13..].iter().all(|&v| v.is_finite() && v >= 0.0));
    }

    #[test]
    fn test_calculate_macd_wrapper() {
        let data = make_data(100);
        let result = calculate_macd(&data, 5, 13, 5).unwrap();
        assert_eq!(result.macd_line.len(), 100);
        assert_eq!(result.signal_line.len(), 100);
        assert_eq!(result.histogram.len(), 100);
    }

    #[test]
    fn test_calculate_bollinger_wrapper() {
        let data = make_data(100);
        let result = calculate_bollinger(&data, 20, 2.0).unwrap();
        assert_eq!(result.upper.len(), 100);
        assert_eq!(result.middle.len(), 100);
        assert_eq!(result.lower.len(), 100);
    }

    #[test]
    fn test_wrappers_propagate_empty_error() {
        assert!(calculate_rsi(&[], 14).is_err());
        assert!(calculate_sma(&[], 14).is_err());
        assert!(calculate_ema(&[], 14).is_err());
        assert!(calculate_atr(&[], &[], &[], 14).is_err());
        assert!(calculate_macd(&[], 5, 13, 5).is_err());
        assert!(calculate_bollinger(&[], 20, 2.0).is_err());
    }

    #[test]
    fn test_calc_rsi_ffi_null_pointers() {
        let result = calc_rsi(
            std::ptr::null(),
            0,
            14,
            std::ptr::null_mut(),
            std::ptr::null_mut(),
        );
        assert_eq!(result, -1);
    }

    #[test]
    fn test_calc_rsi_ffi_empty_data() {
        let data = [];
        let mut out = [0.0_f64; 1];
        let mut out_len: usize = 0;
        let result = calc_rsi(
            data.as_ptr(),
            data.len(),
            14,
            out.as_mut_ptr(),
            &mut out_len as *mut usize,
        );
        assert_eq!(result, -2);
    }

    #[test]
    fn test_calc_rsi_ffi_happy_path() {
        let data: Vec<f64> = (0..100).map(|i| 100.0 + i as f64).collect();
        let mut out = vec![0.0_f64; data.len()];
        let mut out_len: usize = 0;
        let result = calc_rsi(
            data.as_ptr(),
            data.len(),
            14,
            out.as_mut_ptr(),
            &mut out_len as *mut usize,
        );
        assert_eq!(result, 0);
        assert_eq!(out_len, data.len());
        assert!(!out[out_len - 1].is_nan());
    }

    #[test]
    fn test_calc_rsi_ffi_output_written() {
        let data: Vec<f64> = (0..100).map(|i| 100.0 + i as f64).collect();
        let mut out = vec![0.0_f64; data.len()];
        let mut out_len: usize = 0;
        let _ = calc_rsi(
            data.as_ptr(),
            data.len(),
            14,
            out.as_mut_ptr(),
            &mut out_len as *mut usize,
        );
        let last = out[out_len - 1];
        assert!(last > 90.0 || last.is_nan());
    }
}
