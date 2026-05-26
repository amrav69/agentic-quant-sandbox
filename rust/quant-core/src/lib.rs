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

/// Pure Rust MACD calculation.
pub fn calculate_macd(prices: &[f64], fast: usize, slow: usize, signal: usize) -> Result<indicators::MacdOutput, QuantError> {
    indicators::macd(prices, fast, slow, signal)
}

/// Pure Rust Bollinger Bands calculation.
pub fn calculate_bollinger(prices: &[f64], period: usize, std_dev: f64) -> Result<indicators::BollingerOutput, QuantError> {
    indicators::bollinger_bands(prices, period, std_dev)
}

extern "C" fn calc_rsi_impl(prices: *const f64, len: usize, period: usize, out: *mut f64, out_len: *mut usize) -> i32 {
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
    use pyo3::prelude::*;
    use pyo3::PyResult;
    use crate::calculate_rsi;

    #[pyfunction]
    pub fn calculate_rsi_py(prices: Vec<f64>, period: usize) -> PyResult<Vec<f64>> {
        calculate_rsi(&prices, period)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
    }

    #[pymodule]
    fn quant_core(_py: Python, m: &PyModule) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(calculate_rsi_py, m)?)?;
        Ok(())
    }
}
