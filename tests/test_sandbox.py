"""Tests para el sandbox multicontexto."""
import pytest
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
    FreeClientArbitrageSimulator
)
from open_bess_sandbox.compare_runner import run_all_parallel

def test_taxonomy_fail_closed_on_experimental_rules():
    rules = get_standard_rules(InstallationType.FREE_CLIENT_ARBITRAGE)
    ctx = InstallationContext(
        installation_type=InstallationType.FREE_CLIENT_ARBITRAGE,
        site_id="SITE-SANTIAGO-01",
        connection_point="Barra 12 kV Distribucion",
        command_authority=CommandAuthority.BESSAI_OPTIMIZER,
        rules=rules,
        allow_experimental_rules=False
    )
    with pytest.raises(ValueError, match="no puede ejecutarse en modo productivo"):
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

def test_btm_site_meter_peak_shaving():
    meter = SiteLoadMeter(base_kw=500.0, peak_kw=1200.0)
    off_peak = meter.read_at_hour(12.0)
    assert not off_peak.is_peak_hour
    assert off_peak.p_load_kw < 600.0

    peak = meter.read_at_hour(20.0)
    assert peak.is_peak_hour
    assert peak.p_load_kw > 1000.0

def test_all_scenarios_run_parallel():
    results = run_all_parallel()
    assert len(results) == 4
    for r in results:
        assert r.safety_violations == 0
        assert r.rule_compliance_score_pct == 100.0
        assert r.energy_discharged_kwh >= 0.0
