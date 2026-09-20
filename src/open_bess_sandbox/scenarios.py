from dataclasses import dataclass
from typing import Dict, Any, List
from .meters import SiteLoadMeter, SolarGenerationMeter
from .taxonomy import InstallationType, get_standard_rules

@dataclass
class SimulationResult:
    context_type: InstallationType
    energy_discharged_kwh: float
    energy_charged_kwh: float
    peak_metric: str
    primary_kpi_value: float
    primary_kpi_unit: str
    safety_violations: int
    rule_compliance_score_pct: float

class UtilitySSCCSimulator:
    """Escenario 1: Planta Utility en Transmision prestando FFR + Volt/VAR."""
    def __init__(self, p_nom_kw: float = 1000.0, e_nom_kwh: float = 2000.0):
        self.p_nom = p_nom_kw
        self.e_nom = e_nom_kwh

    def run(self, f_grid_hz: float = 49.65, duration_s: float = 10.0) -> SimulationResult:
        delta_f = 50.0 - f_grid_hz
        p_ffr = min(self.p_nom, 1000.0 * (max(0.0, delta_f - 0.05) / 1.4))
        energy_kwh = (p_ffr * duration_s) / 3600.0
        return SimulationResult(
            context_type=InstallationType.UTILITY_SSCC,
            energy_discharged_kwh=round(energy_kwh, 2),
            energy_charged_kwh=0.0,
            peak_metric="Respuesta Contingente FFR",
            primary_kpi_value=round(p_ffr, 1),
            primary_kpi_unit="kW (<500ms)",
            safety_violations=0,
            rule_compliance_score_pct=100.0
        )

class GeneratorFirmSimulator:
    """Escenario 2: Respaldo de Generacion (Solar 3 MWp + BESS 1.5 MW / 3 MWh)."""
    def __init__(self, p_bess_kw: float = 1000.0, line_limit_kw: float = 2000.0):
        self.solar_meter = SolarGenerationMeter(capacity_kwp=3000.0, line_limit_kw=line_limit_kw)
        self.p_bess_kw = p_bess_kw

    def run_24h(self) -> SimulationResult:
        curtailment_prevented_kwh = 0.0
        night_discharge_kwh = 0.0
        for step in range(48):
            h = step * 0.5
            r = self.solar_meter.read_at_hour(h)
            if r["curtailment_risk_kw"] > 0:
                charge_p = min(self.p_bess_kw, r["curtailment_risk_kw"])
                curtailment_prevented_kwh += charge_p * 0.5
            elif 19.0 <= h <= 23.0:
                discharge_p = min(self.p_bess_kw, 750.0)
                night_discharge_kwh += discharge_p * 0.5

        return SimulationResult(
            context_type=InstallationType.GENERATOR_FIRM,
            energy_discharged_kwh=round(night_discharge_kwh, 1),
            energy_charged_kwh=round(curtailment_prevented_kwh, 1),
            peak_metric="Vertimiento Renovable Evitado",
            primary_kpi_value=round(curtailment_prevented_kwh, 1),
            primary_kpi_unit="kWh mitigados",
            safety_violations=0,
            rule_compliance_score_pct=100.0
        )

class BTMPeakShavingSimulator:
    """Escenario 3: Cliente Industrial BTM - Rasurado de Potencia en Hora Punta (18-22h)."""
    def __init__(self, p_cap_target_kw: float = 800.0, p_bess_kw: float = 400.0):
        self.load_meter = SiteLoadMeter(base_kw=500.0, peak_kw=1150.0)
        self.p_cap_target_kw = p_cap_target_kw
        self.p_bess_kw = p_bess_kw

    def run_peak_window(self) -> SimulationResult:
        total_shaved_kwh = 0.0
        max_shaved_kw = 0.0
        for step in range(48):
            h = 18.0 + (step * 5.0 / 60.0)
            reading = self.load_meter.read_at_hour(h)
            if reading.p_load_kw > self.p_cap_target_kw:
                needed_kw = reading.p_load_kw - self.p_cap_target_kw
                actual_kw = min(self.p_bess_kw, needed_kw)
                actual_kw = min(actual_kw, reading.p_load_kw)
                total_shaved_kwh += (actual_kw * (5.0 / 60.0))
                max_shaved_kw = max(max_shaved_kw, actual_kw)

        return SimulationResult(
            context_type=InstallationType.BTM_PEAK_SHAVING,
            energy_discharged_kwh=round(total_shaved_kwh, 1),
            energy_charged_kwh=0.0,
            peak_metric="Recorte Maximo Demanda",
            primary_kpi_value=round(max_shaved_kw, 1),
            primary_kpi_unit="kW reducidos en punta",
            safety_violations=0,
            rule_compliance_score_pct=100.0
        )

class FreeClientArbitrageSimulator:
    """Escenario 4: Arbitraje horario PPA / Precio marginal."""
    def __init__(self, p_bess_kw: float = 500.0, e_nom_kwh: float = 1000.0, eta_rt: float = 0.90):
        self.p_bess_kw = p_bess_kw
        self.e_nom_kwh = e_nom_kwh
        self.eta_rt = eta_rt

    def run_daily_arbitrage(self) -> SimulationResult:
        charge_kwh = min(self.e_nom_kwh * 0.8, self.p_bess_kw * 4.0)
        cost_charge_usd = charge_kwh * 0.015
        discharge_kwh = charge_kwh * self.eta_rt
        revenue_discharge_usd = discharge_kwh * 0.110
        net_spread_usd = revenue_discharge_usd - cost_charge_usd

        return SimulationResult(
            context_type=InstallationType.FREE_CLIENT_ARBITRAGE,
            energy_discharged_kwh=round(discharge_kwh, 1),
            energy_charged_kwh=round(charge_kwh, 1),
            peak_metric="Margen Neto Arbitraje",
            primary_kpi_value=round(net_spread_usd, 2),
            primary_kpi_unit="USD/dia",
            safety_violations=0,
            rule_compliance_score_pct=100.0
        )
