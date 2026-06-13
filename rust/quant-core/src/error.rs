use thiserror::Error;

#[derive(Error, Debug)]
pub enum QuantError {
    #[error("Empty input data provided")]
    EmptyInput,

    #[error("Insufficient data: need at least {required} elements, got {available}")]
    InsufficientData { required: usize, available: usize },

    #[error("Internal error: {0}")]
    Internal(String),

    #[error("FFI error: {0}")]
    Ffi(String),
}
