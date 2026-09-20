from dataclasses import dataclass
import math

@dataclass
class SiteLoadReading:
    p_load_kw: float
    q_load_kvar: float
    is_peak_hour: bool

class SiteLoadMeter:
    """Simula un medidor de carga industrial en baja/media tension."""
    def __init__(self, base_kw: float = 500.0, peak_kw: float = 1150.0):
        self.base_kw = base_kw
        self.peak_kw = peak_kw

    def read_at_hour(self, hour: float) -> SiteLoadReading:
        is_peak = 18.0 <= (hour % 24.0) < 22.0
        if is_peak:
            variation = math.sin((hour - 18.0) * math.pi / 4.0) * (self.peak_kw - self.base_kw)
            p = self.base_kw + max(0.0, variation)
        else:
            p = self.base_kw + 80.0 * math.sin(hour * math.pi / 12.0)
        q = p * 0.25
        return SiteLoadReading(p_load_kw=p, q_load_kvar=q, is_peak_hour=is_peak)

class SolarGenerationMeter:
    """Simula la generacion bruta de una planta fotovoltaica de 3000 kWp."""
    def __init__(self, capacity_kwp: float = 3000.0, line_limit_kw: float = 2000.0):
        self.capacity_kwp = capacity_kwp
        self.line_limit_kw = line_limit_kw

    def read_at_hour(self, hour: float) -> dict:
        h = hour % 24.0
        if 6.5 <= h <= 19.5:
            p_gen = self.capacity_kwp * math.sin((h - 6.5) * math.pi / 13.0)
        else:
            p_gen = 0.0
        curtailment_risk_kw = max(0.0, p_gen - self.line_limit_kw)
        return {
            "p_gen_kw": p_gen,
            "curtailment_risk_kw": curtailment_risk_kw,
            "line_limit_kw": self.line_limit_kw
        }
