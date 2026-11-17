"""Seeded synthetic generator for AML alerts, cases and investigators.

All output is synthetic. No real institution's data, rates or volumes are used.
Run: python -m src.simulate [--seed N]
"""
from __future__ import annotations

import argparse
import heapq
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

from . import config as C


# Queue discipline: risk band first (High, Medium, Low), then oldest first. With
# probability FIFO_PICK_PROB an investigator instead takes the oldest alert in the
# queue regardless of band (imperfect prioritization).
BAND_RANK = {"High": 0, "Medium": 1, "Low": 2}
FIFO_PICK_PROB = 0.15
# Share of High/Medium alerts that enter the Low-priority lane (late risk-score
# enrichment / misrouting), so they wait like Low alerts until reached by FIFO.
MISROUTE_PROB = 0.12


def month_starts() -> list[date]:
    out = []
    y, m = C.START_DATE.year, C.START_DATE.month
    for _ in range(C.N_MONTHS):
        out.append(date(y, m, 1))
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


def business_days(first: date, last: date) -> list[date]:
    d, out = first, []
    while d <= last:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def month_end(d: date) -> date:
    nxt = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
    return nxt - timedelta(days=1)


def baseline_volume(month_idx: int, month: int, rng: np.random.Generator) -> int:
    """trend x seasonality x lognormal noise (no shock)."""
    trend = C.BASE_VOLUME + C.TREND_PER_MONTH * month_idx
    season = (
        1
        + C.SEASON_AMP_1 * np.cos(2 * np.pi * (month - 12) / 12)
        + C.SEASON_AMP_2 * np.cos(4 * np.pi * (month - 3) / 12)
    )
    noise = np.exp(rng.normal(0, C.NOISE_SIGMA))
    return int(round(trend * season * noise))


def _build_roster(rng: np.random.Generator, end: date) -> pd.DataFrame:
    """Initial investigators, random attrition, backfills, cluster and planned hires."""
    rows = []
    n = 0

    def new_id() -> str:
        nonlocal n
        n += 1
        return f"INV-{n:03d}"

    for _ in range(C.N_INVESTIGATORS_START):
        hire = C.START_DATE - timedelta(days=int(rng.integers(120, 1600)))
        rows.append({"investigator_id": new_id(), "hire_date": hire, "term_date": None})

    days = business_days(C.START_DATE, end)
    p_day = 1 - (1 - C.MONTHLY_ATTRITION) ** (1 / 21)
    pending_hires: list[date] = [d for d, k in C.PLANNED_HIRES for _ in range(k)]
    for d in days:
        # starts scheduled for today
        for h in [h for h in pending_hires if h <= d]:
            pending_hires.remove(h)
            rows.append({"investigator_id": new_id(), "hire_date": h, "term_date": None})
        active = [r for r in rows if r["term_date"] is None and r["hire_date"] <= d]
        leavers = []
        if d == C.ATTRITION_CLUSTER[0]:
            tenured = [r for r in active if (d - r["hire_date"]).days > 365]
            idx = rng.choice(len(tenured), size=min(C.ATTRITION_CLUSTER[1], len(tenured)), replace=False)
            leavers += [tenured[i] for i in idx]
        for r in active:
            if r not in leavers and rng.random() < p_day:
                leavers.append(r)
        for r in leavers:
            r["term_date"] = d
            # backfill only for random attrition and cluster leavers alike
            lag = int(rng.integers(C.BACKFILL_LAG_DAYS[0], C.BACKFILL_LAG_DAYS[1] + 1))
            pending_hires.append(d + timedelta(days=lag))
    return pd.DataFrame(rows)


def simulate(seed: int = C.SEED) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    months = month_starts()
    end = month_end(months[-1])

    roster = _build_roster(rng, end)
    speed = {i: float(np.exp(rng.normal(0, C.INVESTIGATOR_SPEED_SIGMA))) for i in roster["investigator_id"]}

    # ---- alerts: arrivals ------------------------------------------------
    recs = []  # (day, scenario)
    for mi, ms in enumerate(months):
        bdays = business_days(ms, month_end(ms))
        base_n = baseline_volume(mi, ms.month, rng)
        shares = np.array([C.SCENARIOS[s]["share"] for s in C.BASELINE_SCENARIOS])
        counts = rng.multinomial(base_n, shares / shares.sum())
        scen_counts = dict(zip(C.BASELINE_SCENARIOS, counts))
        if mi >= C.SHOCK_MONTH_INDEX:
            scen_counts[C.SHOCK_SCENARIO] = int(round(C.SHOCK_VOLUME_SHARE * base_n))
        for scen, k in scen_counts.items():
            day_idx = rng.integers(0, len(bdays), size=k)
            recs.extend((bdays[i], scen) for i in day_idx)
    recs.sort(key=lambda r: r[0])
    n = len(recs)
    day = [r[0] for r in recs]
    scen = np.array([r[1] for r in recs])

    band = np.empty(n, dtype=object)
    score = np.zeros(n, dtype=int)
    base_handle = np.zeros(n)
    escalate = np.zeros(n, dtype=bool)
    for s, p in C.SCENARIOS.items():
        idx = np.where(scen == s)[0]
        if len(idx) == 0:
            continue
        b = rng.choice(["Low", "Medium", "High"], size=len(idx), p=p["bands"])
        band[idx] = b
        for bb, (lo, hi) in C.BAND_SCORE_RANGE.items():
            m = b == bb
            score[idx[m]] = rng.integers(lo, hi + 1, size=m.sum())
        base_handle[idx] = np.clip(
            p["median"] * np.exp(rng.normal(0, p["sigma"], size=len(idx))), 5, 480
        )
        pesc = np.clip(p["esc"] * np.array([C.BAND_ESC_MULT[x] for x in b]), 0, 0.95)
        escalate[idx] = rng.random(len(idx)) < pesc
    sla = np.array([C.SLA_DAYS[b] for b in band])
    created_off = rng.integers(0, 6 * 3600, size=n)  # overnight batch, 00:00-05:59
    created_at = [datetime.combine(d, datetime.min.time()) + timedelta(seconds=int(o)) for d, o in zip(day, created_off)]

    # ---- work the queue day by day (risk band first, with a FIFO exception) -----------
    arrivals: dict[date, list[int]] = {}
    for i, d in enumerate(day):
        arrivals.setdefault(d, []).append(i)

    misroute = rng.random(n) < MISROUTE_PROB
    closed_day = np.full(n, None, dtype=object)
    closed_by = np.full(n, None, dtype=object)
    handle = np.full(n, np.nan)
    heap: list[tuple[int, int]] = []   # (band rank, alert index); index order = creation order
    fifo: list[tuple[int, int]] = []
    carry = {i: 0.0 for i in roster["investigator_id"]}
    n_open = [0]
    C_FIFO = FIFO_PICK_PROB
    hire = dict(zip(roster["investigator_id"], roster["hire_date"]))
    term = dict(zip(roster["investigator_id"], roster["term_date"]))
    for d in business_days(C.START_DATE, end):
        for i in arrivals.get(d, []):
            rank = 2 if (band[i] != "Low" and misroute[i]) else BAND_RANK[band[i]]
            heapq.heappush(heap, (rank, i))
            heapq.heappush(fifo, (i, i))
            n_open[0] += 1
        active = [k for k in hire if hire[k] <= d and (term[k] is None or term[k] > d)]
        order = rng.permutation(len(active))
        for oi in order:
            inv = active[oi]
            if rng.random() < C.SHRINKAGE:
                continue
            tenure = (d - hire[inv]).days / C.DAYS_PER_MONTH
            minutes = C.PRODUCTIVE_MIN_PER_DAY * C.ramp_factor(tenure) + carry[inv]
            while minutes > 0 and n_open[0] > 0:
                q = fifo if rng.random() < C_FIFO else heap
                i = heapq.heappop(q)[1]
                while closed_day[i] is not None:  # lazily skip alerts closed via the other heap
                    i = heapq.heappop(q)[1]
                n_open[0] -= 1
                h = base_handle[i] * speed[inv]
                handle[i] = h
                closed_day[i] = d
                closed_by[i] = inv
                minutes -= h
            carry[inv] = min(minutes, 0.0)

    closed_off = rng.integers(9 * 3600, 17 * 3600, size=n)
    closed_at = [
        datetime.combine(d, datetime.min.time()) + timedelta(seconds=int(o)) if d is not None else pd.NaT
        for d, o in zip(closed_day, closed_off)
    ]
    disposition = np.where(
        closed_day == None,  # noqa: E711
        None,
        np.where(escalate, "escalated_to_case", "closed_no_action"),
    )
    alerts = pd.DataFrame(
        {
            "alert_id": [f"AL-{i + 1:06d}" for i in range(n)],
            "created_at": pd.to_datetime(created_at),
            "scenario": scen,
            "risk_band": band,
            "risk_score": score,
            "sla_days": sla,
            "handle_minutes": np.round(handle, 1),
            "assigned_investigator_id": closed_by,
            "closed_at": pd.to_datetime(closed_at),
            "disposition": disposition,
        }
    )

    # ---- cases ---------------------------------------------------------------
    esc_idx = np.where(disposition == "escalated_to_case")[0]
    opened = [pd.Timestamp(closed_at[i]) for i in esc_idx]
    sar_p = np.array(
        [min(C.SCENARIOS[scen[i]]["sar"] * C.BAND_SAR_MULT[band[i]], 0.95) for i in esc_idx]
    )
    sar_draw = rng.random(len(esc_idx)) < sar_p
    dur = np.exp(rng.normal(np.log(C.CASE_DAYS_MEDIAN), C.CASE_DAYS_SIGMA, size=len(esc_idx)))
    case_closed = [o + pd.Timedelta(days=float(x)) for o, x in zip(opened, dur)]
    end_ts = pd.Timestamp(end) + pd.Timedelta(days=1)
    is_closed = np.array([c < end_ts for c in case_closed])
    cases = pd.DataFrame(
        {
            "case_id": [f"CS-{k + 1:06d}" for k in range(len(esc_idx))],
            "alert_id": alerts["alert_id"].values[esc_idx],
            "opened_at": opened,
            "closed_at": [c if ok else pd.NaT for c, ok in zip(case_closed, is_closed)],
            "investigator_id": closed_by[esc_idx],
            "sar_filed": [bool(s) if ok else None for s, ok in zip(sar_draw, is_closed)],
        }
    )
    cases["sar_filed"] = cases["sar_filed"].astype("boolean")
    cases["opened_at"] = pd.to_datetime(cases["opened_at"])
    cases["closed_at"] = pd.to_datetime(cases["closed_at"])

    investigators = roster.copy()
    investigators["hire_date"] = pd.to_datetime(investigators["hire_date"])
    investigators["term_date"] = pd.to_datetime(investigators["term_date"])
    return {"alerts": alerts, "cases": cases, "investigators": investigators}


def write(tables: dict[str, pd.DataFrame]) -> None:
    C.RAW_DIR.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_csv(C.RAW_DIR / f"{name}.csv", index=False)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=C.SEED)
    args = ap.parse_args()
    t = simulate(args.seed)
    write(t)
    a = t["alerts"]
    print(
        f"Simulated {len(a):,} alerts, {len(t['cases']):,} cases, "
        f"{len(t['investigators'])} investigators (seed={args.seed}); "
        f"{a['closed_at'].isna().sum():,} alerts open at end of window."
    )


if __name__ == "__main__":
    main()
