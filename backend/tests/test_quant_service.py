from app.database import SessionLocal
from app.quant import service


def test_price_history_is_one_aligned_wide_frame(client):
    db = SessionLocal()
    try:
        prices = service.load_prices(db)
    finally:
        db.close()

    assert prices.shape == (520, 30)
    assert prices.index.is_monotonic_increasing
    assert not prices.isna().any().any()


def test_cached_scores_match_a_fresh_computation(client):
    db = SessionLocal()
    try:
        cached, _ = service.compute_quant_scores(db)
        cached["composite_score"] = 0.0  # callers get a copy, so this must not leak into the cache
        service.clear_cache()
        fresh, _ = service.compute_quant_scores(db)
        again, _ = service.compute_quant_scores(db)
    finally:
        db.close()

    assert fresh.equals(again)
    assert (fresh["composite_score"] != 0.0).any()
