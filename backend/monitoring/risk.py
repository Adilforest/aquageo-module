"""Risk detectors over HydropostReading series (issue #18).

Architecture (CLAUDE.md §9): a ``RiskDetector`` interface + registry, so new
detectors are added without rewriting the core. Forecasting is a separate
swappable ``ForecastModel`` interface.

Each detector returns a JSON-serialisable dict:
    {detector, level, score, explanation, factors, ...}
level ∈ {none, watch, high, critical}. Thresholds are fixed by the spec.
"""
from __future__ import annotations

import statistics
from datetime import timedelta

RISK_LEVELS = ["none", "watch", "high", "critical"]

FLOOD_MONTHS = {4, 5, 6}
LOW_WATER_MONTHS = {7, 8, 9}


def _rank(level: str) -> int:
    return RISK_LEVELS.index(level)


def _escalate(level: str, steps: int = 1) -> str:
    return RISK_LEVELS[min(len(RISK_LEVELS) - 1, _rank(level) + steps)]


def _season_months(month: int) -> set[int]:
    if month in FLOOD_MONTHS:
        return FLOOD_MONTHS
    if month in LOW_WATER_MONTHS:
        return LOW_WATER_MONTHS
    return set(range(1, 13)) - FLOOD_MONTHS - LOW_WATER_MONTHS


# --- detector registry -----------------------------------------------------
_DETECTORS: list = []


def register(detector):
    _DETECTORS.append(detector)
    return detector


class RiskDetector:
    code = "base"

    def evaluate(self, structure, readings) -> dict:  # pragma: no cover - interface
        raise NotImplementedError

    def _empty(self, reason: str) -> dict:
        return {"detector": self.code, "level": "none", "score": None,
                "explanation": reason, "factors": []}


# --- detector 1: flood -----------------------------------------------------
class FloodDetector(RiskDetector):
    code = "flood"

    def evaluate(self, structure, readings) -> dict:
        last = readings[-1]
        danger = last.danger_level
        level = last.water_level
        if not danger or level is None:
            return self._empty("нет уровня/опасного уровня")

        r = level / danger
        if r < 0.8:
            base = "none"
        elif r < 0.9:
            base = "watch"
        elif r < 1.0:
            base = "high"
        else:
            base = "critical"

        factors = [{"code": "ratio", "detail": f"уровень/опасный = {r:.2f}"}]

        # growth modifier: rise over last 3 days >= 10% of danger
        target = last.ts - timedelta(days=3)
        prior = next((rd for rd in reversed(readings[:-1]) if rd.ts <= target), None)
        final = base
        delta_ratio = 0.0
        if prior and prior.water_level is not None:
            delta_ratio = (level - prior.water_level) / danger
            if delta_ratio >= 0.10:
                final = _escalate(base, 1)
                factors.append({"code": "fast_rise", "detail":
                                f"рост за 3 дня = {delta_ratio:.0%} от опасного (+1 ступень)"})

        return {
            "detector": self.code, "level": final, "score": round(r, 3),
            "explanation": f"r={r:.2f}, тренд 3д={delta_ratio:+.0%}, уровень риска {final}",
            "factors": factors,
        }


# --- detector 2: low water / drought --------------------------------------
class LowWaterDetector(RiskDetector):
    code = "low_water"

    def evaluate(self, structure, readings) -> dict:
        last = readings[-1]
        if last.discharge is None:
            return self._empty("нет расхода")
        months = _season_months(last.ts.month)
        season_q = [
            r.discharge for r in readings
            if r.discharge is not None and r.ts.month in months
        ]
        if not season_q:
            return self._empty("нет данных по сезону")
        median = statistics.median(season_q)
        if not median:
            return self._empty("сезонная норма = 0")

        q = last.discharge / median
        if q >= 0.5:
            base = "none"
        elif q >= 0.3:
            base = "watch"
        else:
            base = "high"

        # sustained drought: consecutive trailing days below 0.5 of seasonal norm
        streak = 0
        for rd in reversed(readings):
            if rd.discharge is not None and rd.discharge / median < 0.5:
                streak += 1
            else:
                break
        final = base
        factors = [
            {"code": "q", "detail": f"расход/сезонная норма = {q:.2f}"},
            {"code": "seasonal_median", "detail": f"норма сезона = {median:.2f}"},
            {"code": "streak", "detail": f"дней подряд ниже нормы: {streak}"},
        ]
        if base != "none" and streak >= 14:
            final = _escalate(base, 1)
            factors.append({"code": "sustained", "detail": "просадка >=14 дней (+1 ступень)"})

        return {
            "detector": self.code, "level": final, "score": round(q, 3),
            "explanation": f"q={q:.2f} (норма {median:.1f}), {streak} дн. ниже нормы -> {final}",
            "factors": factors,
        }


# --- forecast model (swappable) -------------------------------------------
class ForecastModel:
    name = "base"

    def predict(self, levels: list[float], horizon: int) -> list[float]:  # pragma: no cover
        raise NotImplementedError


class LinearTrendForecast(ForecastModel):
    """Least-squares linear trend over the last N days (no ARIMA/Prophet)."""

    name = "linear_trend"

    def __init__(self, window: int = 14):
        self.window = window

    def predict(self, levels: list[float], horizon: int) -> list[float]:
        series = levels[-self.window:]
        n = len(series)
        if n < 2:
            return [series[-1]] * horizon if series else []
        mean_x = (n - 1) / 2
        mean_y = sum(series) / n
        sxx = sum((x - mean_x) ** 2 for x in range(n))
        sxy = sum((x - mean_x) * (y - mean_y) for x, y in zip(range(n), series, strict=False))
        slope = sxy / sxx if sxx else 0.0
        intercept = mean_y - slope * mean_x
        return [intercept + slope * (n - 1 + h) for h in range(1, horizon + 1)]


# --- detector 3: short-term level forecast --------------------------------
class ForecastDetector(RiskDetector):
    code = "forecast"

    def __init__(self, model: ForecastModel | None = None, horizon: int = 7):
        self.model = model or LinearTrendForecast()
        self.horizon = horizon

    def evaluate(self, structure, readings) -> dict:
        last = readings[-1]
        danger = last.danger_level
        levels = [r.water_level for r in readings if r.water_level is not None]
        if len(levels) < 3 or not danger:
            return {**self._empty("недостаточно данных для прогноза"), "estimated": True}

        preds = [round(p, 2) for p in self.model.predict(levels, self.horizon)]
        crossing_day = next((h for h, p in enumerate(preds, 1) if p >= danger), None)
        crosses = crossing_day is not None
        level = "high" if crosses else "none"
        peak = max(preds) if preds else last.water_level

        cross_txt = f"пересечение на день {crossing_day}" if crosses else "опасный не достигается"
        explanation = (
            f"прогноз ({self.model.name}, {self.horizon}д) пик {peak:.1f}; "
            f"{cross_txt} (оценочно)"
        )
        return {
            "detector": self.code, "level": level,
            "score": round(peak / danger, 3) if danger else None,
            "explanation": explanation,
            "factors": [{"code": "model", "detail": self.model.name},
                        {"code": "crosses_danger", "detail": str(crosses)}],
            "estimated": True,
            "horizon_days": self.horizon,
            "predicted": preds,
            "crosses_danger": crosses,
            "crossing_day": crossing_day,
        }


# Register default detector instances (order defines evaluation order).
register(FloodDetector())
register(LowWaterDetector())
register(ForecastDetector())


def compute_risk(structure) -> dict:
    """Run all detectors for a hydropost. Non-hydroposts get an empty risk."""
    if getattr(structure, "type_id", None) != "hydropost":
        return {}
    readings = list(structure.readings.order_by("ts"))
    if not readings:
        return {"detectors": {}, "max_level": "none", "alert": False}

    detectors = {}
    max_level = "none"
    for det in _DETECTORS:
        res = det.evaluate(structure, readings)
        detectors[det.code] = res
        if _rank(res["level"]) > _rank(max_level):
            max_level = res["level"]

    return {
        "detectors": detectors,
        "max_level": max_level,
        "alert": _rank(max_level) >= _rank("high"),
    }
