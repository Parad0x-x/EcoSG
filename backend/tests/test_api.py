import pytest


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_companies_and_sectors(client):
    companies = client.get("/api/companies").json()
    sectors = client.get("/api/sectors").json()

    assert len(companies) == 30
    assert len(sectors) == 10
    tech = client.get("/api/companies", params={"sector": "Technology"}).json()
    assert {c["ticker"] for c in tech} == {"AAPL", "MSFT", "NVDA"}


def test_company_lookup_is_case_insensitive_and_404s(client):
    assert client.get("/api/companies/aapl").json()["ticker"] == "AAPL"
    assert client.get("/api/companies/NOPE").status_code == 404


def test_quant_factors_rank_whole_universe(client):
    rows = client.get("/api/quant/factors").json()

    assert sorted(r["rank"] for r in rows) == list(range(1, 31))
    assert client.get("/api/quant/companies/NOPE").status_code == 404


def test_top_picks_respect_position_cap(client):
    picks = client.get("/api/quant/portfolio/picks").json()

    assert picks
    assert sum(p["target_weight_pct"] for p in picks) == pytest.approx(100, abs=0.1)
    assert all(p["target_weight_pct"] <= 22.0 + 0.01 for p in picks)


def test_portfolio_screen_normalizes_weights(client):
    def screen(w1, w2):
        body = {"holdings": [{"ticker": "AAPL", "weight_pct": w1}, {"ticker": "XOM", "weight_pct": w2}]}
        return client.post("/api/portfolio/screen", json=body).json()

    a, b = screen(50, 50), screen(1, 1)

    assert a["weighted_esg_score"] == b["weighted_esg_score"]
    assert a["weighted_quant_score"] is not None


@pytest.mark.parametrize(
    ("holdings", "status"),
    [([], 400), ([{"ticker": "NOPE", "weight_pct": 10}], 404), ([{"ticker": "AAPL", "weight_pct": 0}], 422)],
)
def test_portfolio_screen_rejects_bad_input(client, holdings, status):
    assert client.post("/api/portfolio/screen", json={"holdings": holdings}).status_code == status


def test_backtest_returns_metrics_and_curve(client):
    body = client.get("/api/quant/backtest").json()

    assert body["equity_curve"]
    assert body["metrics"]["sharpe_ratio"] is not None


def test_portfolio_screen_degrades_to_esg_only_and_logs(client, monkeypatch, caplog):
    from app.quant import service as quant_service

    def boom(_db):
        raise RuntimeError("quant down")

    monkeypatch.setattr(quant_service, "compute_quant_scores", boom)
    body = {"holdings": [{"ticker": "AAPL", "weight_pct": 100}]}

    res = client.post("/api/portfolio/screen", json=body)

    assert res.status_code == 200
    assert res.json()["weighted_quant_score"] is None
    assert "Quant scoring failed" in caplog.text
