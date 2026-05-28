use criterion::{black_box, criterion_group, criterion_main, Criterion};

fn make_data(n: usize) -> Vec<f64> {
    (0..n).map(|i| 100.0 + (i as f64 * 0.5) + (i as f64).sin()).collect()
}

fn bench_sma(c: &mut Criterion) {
    let data = make_data(10_000);
    c.bench_function("sma_10k_period_14", |b| {
        b.iter(|| quant_core::indicators::sma(black_box(&data), 14))
    });
}

fn bench_ema(c: &mut Criterion) {
    let data = make_data(10_000);
    c.bench_function("ema_10k_period_14", |b| {
        b.iter(|| quant_core::indicators::ema(black_box(&data), 14))
    });
}

fn bench_rsi(c: &mut Criterion) {
    let data = make_data(10_000);
    c.bench_function("rsi_10k_period_14", |b| {
        b.iter(|| quant_core::indicators::rsi(black_box(&data), 14))
    });
}

fn bench_macd(c: &mut Criterion) {
    let data = make_data(10_000);
    c.bench_function("macd_10k_fast5_slow13_signal5", |b| {
        b.iter(|| quant_core::indicators::macd(black_box(&data), 5, 13, 5))
    });
}

fn bench_bollinger(c: &mut Criterion) {
    let data = make_data(10_000);
    c.bench_function("bollinger_10k_period_20_stddev_2", |b| {
        b.iter(|| quant_core::indicators::bollinger_bands(black_box(&data), 20, 2.0))
    });
}

fn bench_highest(c: &mut Criterion) {
    let data = make_data(10_000);
    c.bench_function("highest_10k_period_14", |b| {
        b.iter(|| quant_core::indicators::highest(black_box(&data), 14))
    });
}

fn bench_lowest(c: &mut Criterion) {
    let data = make_data(10_000);
    c.bench_function("lowest_10k_period_14", |b| {
        b.iter(|| quant_core::indicators::lowest(black_box(&data), 14))
    });
}

criterion_group!(
    name = indicator_benches;
    config = Criterion::default().sample_size(100).warm_up_time(std::time::Duration::from_secs(1)).measurement_time(std::time::Duration::from_secs(3));
    targets = bench_sma, bench_ema, bench_rsi, bench_macd, bench_bollinger, bench_highest, bench_lowest
);
criterion_main!(indicator_benches);
