import concurrent.futures
from typing import List
from .taxonomy import InstallationType
from .scenarios import (
    UtilitySSCCSimulator,
    GeneratorFirmSimulator,
    BTMPeakShavingSimulator,
    FreeClientArbitrageSimulator,
    SimulationResult
)

def run_all_parallel() -> List[SimulationResult]:
    sims = [
        (InstallationType.UTILITY_SSCC, lambda: UtilitySSCCSimulator().run()),
        (InstallationType.GENERATOR_FIRM, lambda: GeneratorFirmSimulator().run_24h()),
        (InstallationType.BTM_PEAK_SHAVING, lambda: BTMPeakShavingSimulator().run_peak_window()),
        (InstallationType.FREE_CLIENT_ARBITRAGE, lambda: FreeClientArbitrageSimulator().run_daily_arbitrage()),
    ]
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(fn): itype for itype, fn in sims}
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
    
    results.sort(key=lambda r: r.context_type.value)
    return results

def print_comparison_table(results: List[SimulationResult]) -> str:
    lines = [
        "| Contexto Operativo | Descarga (kWh) | Carga (kWh) | Indicador Clave (KPI) | Fugas de Seguridad | Conformidad |",
        "|---|---|---|---|---|---|"
    ]
    for r in results:
        lines.append(
            f"| **{r.context_type.value}** | {r.energy_discharged_kwh:.1f} | {r.energy_charged_kwh:.1f} | "
            f"{r.peak_metric}: **{r.primary_kpi_value} {r.primary_kpi_unit}** | {r.safety_violations} | {r.rule_compliance_score_pct:.0f}% |"
        )
    table = "\n".join(lines)
    print("\n" + "=" * 80)
    print("OPEN BESS SANDBOX — RESULTADOS COMPARATIVOS MULTICONTEXTO EN PARALELO")
    print("=" * 80)
    print(table)
    print("=" * 80 + "\n")
    return table

if __name__ == "__main__":
    res = run_all_parallel()
    print_comparison_table(res)
