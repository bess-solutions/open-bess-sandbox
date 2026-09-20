"""Tests exhaustivos para el sandbox multicontexto chileno y conexion con Open BESS Edge."""
import pytest
import asyncio
from open_bess_sandbox.taxonomy import (
    InstallationType,
    CommandAuthority,
    InstallationContext,
    get_standard_rules,
    RegulatoryStatus
)
from open_bess_sandbox.meters import SiteLoadMeter, SolarGenerationMeter
from open_bess_sandbox.scenarios import (
    UtilitySSCCSimulator,
    GeneratorFirmSimulator,
    BTMPeakShavingSimulator,
    FreeClientArbitrageSimulator,
    EdgeIntegratedSSCCSimulator,
    EDGE_AVAILABLE
)
from open_bess_sandbox.compare_runner import run_all_parallel

def test_taxonomy_fail_closed_on_unverified_assumptions():
    """Reglas en SUPUESTO o EN_EVALUACION fallan closed por defecto en modo productivo."""
    for inst_type in [InstallationType.UTILITY_SSCC, InstallationType.BTM_PEAK_SHAVING, InstallationType.FREE_CLIENT_ARBITRAGE]:
        rules = get_standard_rules(inst_type)
        ctx = InstallationContext(
            installation_type=inst_type,
            site_id="SITE-TEST-01",
            connection_point="Barra de Prueba",
            command_authority=CommandAuthority.PLANT_OPERATOR,
            rules=rules,
            allow_experimental_rules=False
        )
        with pytest.raises(ValueError, match="[Nn]o puede ejecutarse en modo productivo"):
            ctx.validate_fail_closed()

def test_taxonomy_passes_when_experimental_allowed():
    rules = get_standard_rules(InstallationType.FREE_CLIENT_ARBITRAGE)
    ctx = InstallationContext(
        installation_type=InstallationType.FREE_CLIENT_ARBITRAGE,
        site_id="SITE-SANTIAGO-01",
        connection_point="Barra 12 kV Distribucion",
        command_authority=CommandAuthority.BESSAI_OPTIMIZER,
        rules=rules,
        allow_experimental_rules=True
    )
    assert ctx.validate_fail_closed() is True

def test_utility_sscc_rules_documented_as_supuesto():
    rules = get_standard_rules(InstallationType.UTILITY_SSCC)
    assert len(rules) == 2
    for r in rules:
        assert r.status == RegulatoryStatus.SUPUESTO
        assert "Res. Ex. CNE" in r.legal_basis

def test_btm_peak_shaving_rules_documented():
    rules = get_standard_rules(InstallationType.BTM_PEAK_SHAVING)
    assert len(rules) == 2
    for r in rules:
        assert r.status == RegulatoryStatus.SUPUESTO
        assert r.requires_site_meter is True
    assert any("Precios de Nudo Promedio" in r.legal_basis for r in rules)

def test_btm_site_meter_peak_shaving():
    meter = SiteLoadMeter(base_kw=500.0, peak_kw=1200.0)
    off_peak = meter.read_at_hour(12.0)
    assert not off_peak.is_peak_hour
    assert off_peak.p_load_kw < 600.0

    peak = meter.read_at_hour(20.0)
    assert peak.is_peak_hour
    assert peak.p_load_kw > 1000.0

def test_solar_meter_curtailment_calculation():
    meter = SolarGenerationMeter(capacity_kwp=3000.0, line_limit_kw=2000.0)
    night = meter.read_at_hour(2.0)
    assert night["p_gen_kw"] == 0.0
    assert night["curtailment_risk_kw"] == 0.0

    noon = meter.read_at_hour(13.0)
    assert noon["p_gen_kw"] > 2500.0
    assert noon["curtailment_risk_kw"] > 500.0

def test_all_scenarios_run_parallel():
    results = run_all_parallel()
    assert len(results) == 4
    for r in results:
        assert r.safety_violations == 0
        assert r.rule_compliance_score_pct == 100.0
        assert r.energy_discharged_kwh >= 0.0

@pytest.mark.asyncio
async def test_edge_integrated_closed_loop_sscc():
    """Valida la ejecucion de punta a punta importando el motor real de open-bess-edge."""
    if not EDGE_AVAILABLE:
        pytest.skip("open_bess_edge no esta instalado en este entorno de pruebas")
    sim = EdgeIntegratedSSCCSimulator(cycle_ms=100)
    res = await sim.run_frequency_contingency(f_contingency_hz=49.65, duration_s=1.2)
    assert res.context_type == InstallationType.UTILITY_SSCC
    assert res.primary_kpi_value > 0.0
    assert res.safety_violations == 0
    assert res.rule_compliance_score_pct == 100.0
