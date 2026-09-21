from dataclasses import dataclass
from typing import Dict, Any, List
import asyncio
import time

from .meters import SiteLoadMeter, SolarGenerationMeter
from .taxonomy import InstallationType, get_standard_rules

try:
    from open_bess_edge.config import EdgeConfig, parse_config
    from open_bess_edge.runtime.factory import build_node
    from open_bess_edge.sim.runner import SimEnvironment
    EDGE_AVAILABLE = True
except ImportError:
    EDGE_AVAILABLE = False

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
    """Escenario 1: Planta Utility en Transmision prestando FFR + Volt/VAR (Modelo simplificado)."""
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

def _build_sandbox_cfg(cycle_ms: int = 100) -> Any:
    raw = {
        "node": {"device_id": "sandbox-sscc-node"},
        "plant": {"p_nominal_kw": 1000.0, "e_nominal_kwh": 2000.0, "v_nominal_v": 400.0},
        "volt_var": {"q_max_kvar": 600.0},
        "runtime": {"cycle_ms": cycle_ms, "comm_loss_hold_s": 2.0, "startup_valid_cycles": 3},
        "health": {"enabled": False},
    }
    return parse_config(raw, source="<sandbox>")

class EdgeIntegratedSSCCSimulator:
    """Escenario 1 Real: Lazo cerrado completo usando el motor y la envolvente de seguridad de Open BESS Edge."""
    def __init__(self, cycle_ms: int = 100):
        if not EDGE_AVAILABLE:
            raise RuntimeError("open_bess_edge no esta instalado en el entorno.")
        self.cycle_ms = cycle_ms

    async def run_frequency_contingency(self, f_contingency_hz: float = 49.65, duration_s: float = 2.0) -> SimulationResult:
        cfg = _build_sandbox_cfg(cycle_ms=self.cycle_ms)
        env = SimEnvironment(cfg, tick_s=0.01)
        port = await env.start(realtime=True)
        node = build_node(cfg, host="127.0.0.1", port=port)
        started = await node.start()
        if not started:
            await env.stop()
            raise RuntimeError("No se pudo iniciar el nodo Open BESS Edge.")

        task = asyncio.ensure_future(node.run())
        setpoints_written = []
        try:
            # Esperar arranque y validacion inicial de ciclos
            await asyncio.sleep(0.4)
            # Aplicar contingencia de frecuencia
            env.plant.f_hz = f_contingency_hz
            t_start = time.monotonic()
            
            while time.monotonic() - t_start < duration_s:
                await asyncio.sleep(0.05)
                # Inspeccionar logs de escritura del servidor simulado
                for t, addr, vals in env.server.write_log:
                    if addr == 200 and vals != [0]:
                        setpoints_written.append((t, vals[0]))
            
            # Restaurar frecuencia
            env.plant.f_hz = 50.0
            await asyncio.sleep(0.2)
        finally:
            node.request_stop()
            await task
            await node.stop()
            await env.stop()

        max_p_kw = max([p for _, p in setpoints_written], default=0.0)
        max_p_kw = float(max_p_kw)
        energy_kwh = (max_p_kw * duration_s) / 3600.0

        return SimulationResult(
            context_type=InstallationType.UTILITY_SSCC,
            energy_discharged_kwh=round(energy_kwh, 3),
            energy_charged_kwh=0.0,
            peak_metric="Respuesta FFR Lazo Cerrado Edge Real",
            primary_kpi_value=round(max_p_kw, 1),
            primary_kpi_unit="kW inyectados en lazo cerrado",
            safety_violations=node.metrics.trips,
            rule_compliance_score_pct=100.0 if len(setpoints_written) > 0 else 0.0
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


def _build_btm_sandbox_cfg(
    p_bess_kw: float = 1000.0,
    e_bess_kwh: float = 2000.0,
    max_grid_import_kw: float = 1200.0,
    soc_reserve_pct: float = 20.0,
    cycle_ms: int = 100,
):
    raw = {
        "node": {"device_id": "sandbox-btm-node"},
        "plant": {"p_nominal_kw": p_bess_kw, "e_nominal_kwh": e_bess_kwh, "v_nominal_v": 400.0},
        "volt_var": {"mode": "DISABLED"},
        "installation": {
            "role": "btm_peak_shaving",
            "constraints": {
                "max_grid_import_kw": max_grid_import_kw,
                "max_grid_export_kw": 0.0,
                "soc_reserve_pct": soc_reserve_pct,
                "p_grid_timeout_s": 2.0,
            },
            "dispatch_sources": [{"type": "http_bearer"}],
            "metadata": {
                "policy_compiler": "open-bess-sandbox",
                "rule_set_id": "CL-PEAK-TARIFF-2026",
                "status": "SUPUESTO",
            },
            "accept_unverified_rule_set": True,
        },
        "grid_meter": {"port": 1502},
        "runtime": {"cycle_ms": cycle_ms, "comm_loss_hold_s": 2.0, "startup_valid_cycles": 3},
        "health": {"enabled": False},
    }
    return parse_config(raw, source="<sandbox-btm>")


class EdgeIntegratedBTMPeakShavingSimulator:
    """Escenario 3 Real: Lazo cerrado completo de Peak Shaving BTM usando el modulo de instalacion de Open BESS Edge."""
    def __init__(
        self,
        p_bess_kw: float = 1000.0,
        e_bess_kwh: float = 2000.0,
        max_grid_import_kw: float = 1200.0,
        soc_reserve_pct: float = 20.0,
        cycle_ms: int = 100,
    ):
        if not EDGE_AVAILABLE:
            raise RuntimeError("open_bess_edge no esta instalado en el entorno.")
        self.p_bess_kw = p_bess_kw
        self.e_bess_kwh = e_bess_kwh
        self.max_grid_import_kw = max_grid_import_kw
        self.soc_reserve_pct = soc_reserve_pct
        self.cycle_ms = cycle_ms

    async def run_peak_event(self, site_load_kw: float = 1500.0, duration_s: float = 1.5) -> SimulationResult:
        cfg = _build_btm_sandbox_cfg(
            p_bess_kw=self.p_bess_kw,
            e_bess_kwh=self.e_bess_kwh,
            max_grid_import_kw=self.max_grid_import_kw,
            soc_reserve_pct=self.soc_reserve_pct,
            cycle_ms=self.cycle_ms,
        )
        env = SimEnvironment(cfg, tick_s=0.01)
        port = await env.start(realtime=True)
        node = build_node(
            cfg,
            host="127.0.0.1",
            port=port,
            meter_host="127.0.0.1",
            meter_port=env.meter_port,
        )
        started = await node.start()
        if not started:
            await env.stop()
            raise RuntimeError("No se pudo iniciar el nodo Open BESS Edge para BTM Peak Shaving.")

        task = asyncio.ensure_future(node.run())
        setpoints_written = []
        try:
            # Esperar sincronización y validación de arranque
            await asyncio.sleep(0.4)
            # Aplicar demanda industrial en punta (escalón de carga en el sitio)
            env.plant.site_load_kw = site_load_kw
            t_start = time.monotonic()

            while time.monotonic() - t_start < duration_s:
                await asyncio.sleep(0.05)
                for t, addr, vals in env.server.write_log:
                    if addr == 200 and vals != [0]:
                        setpoints_written.append((t, vals[0]))

            # Normalizar carga a nivel base
            env.plant.site_load_kw = self.max_grid_import_kw * 0.8
            await asyncio.sleep(0.2)
        finally:
            node.request_stop()
            await task
            await node.stop()
            await env.stop()

        max_p_kw = max([p for _, p in setpoints_written], default=0.0)
        max_p_kw = float(max_p_kw)
        energy_kwh = (max_p_kw * duration_s) / 3600.0

        return SimulationResult(
            context_type=InstallationType.BTM_PEAK_SHAVING,
            energy_discharged_kwh=round(energy_kwh, 3),
            energy_charged_kwh=0.0,
            peak_metric="Recorte Demanda Lazo Cerrado Edge Real",
            primary_kpi_value=round(max_p_kw, 1),
            primary_kpi_unit="kW inyectados en lazo cerrado",
            safety_violations=node.metrics.trips,
            rule_compliance_score_pct=100.0 if len(setpoints_written) > 0 else 0.0,
        )

class FreeClientArbitrageSimulator:
    """Escenario 4: Arbitraje horario PPA / Precio marginal."""
    def __init__(self, p_bess_kw: float = 500.0, e_bess_kwh: float = 1000.0):
        self.p_bess_kw = p_bess_kw
        self.e_bess_kwh = e_bess_kwh

    def run_daily_arbitrage(self) -> SimulationResult:
        solar_soak_kwh = self.p_bess_kw * 2.0
        evening_discharge_kwh = min(solar_soak_kwh * 0.9, self.e_bess_kwh * 0.85)

        return SimulationResult(
            context_type=InstallationType.FREE_CLIENT_ARBITRAGE,
            energy_discharged_kwh=round(evening_discharge_kwh, 1),
            energy_charged_kwh=round(solar_soak_kwh, 1),
            peak_metric="Arbitraje Solar-Punta",
            primary_kpi_value=round(evening_discharge_kwh, 1),
            primary_kpi_unit="kWh desplazados",
            safety_violations=0,
            rule_compliance_score_pct=100.0
        )
