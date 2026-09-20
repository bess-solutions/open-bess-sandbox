from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class InstallationType(str, Enum):
    UTILITY_SSCC = "utility_sscc"
    GENERATOR_FIRM = "generator_firm"
    BTM_PEAK_SHAVING = "btm_peak_shaving"
    FREE_CLIENT_ARBITRAGE = "free_client_arbitrage"

class RegulatoryStatus(str, Enum):
    VIGENTE = "vigente"
    EN_EVALUACION = "en_evaluacion"
    SUPUESTO = "supuesto"

class CommandAuthority(str, Enum):
    CEN_SITR = "cen_sitr"
    PLANT_OPERATOR = "plant_operator"
    LOCAL_EMS = "local_ems"
    BESSAI_OPTIMIZER = "bessai_optimizer"

class RegulatoryRule(BaseModel):
    rule_id: str
    description: str
    norm_reference: str
    status: RegulatoryStatus
    requires_site_meter: bool = False
    min_soc_reserve_pct: float = Field(default=10.0, ge=0.0, le=100.0)

class InstallationContext(BaseModel):
    installation_type: InstallationType
    site_id: str
    connection_point: str
    command_authority: CommandAuthority
    rules: List[RegulatoryRule]
    allow_experimental_rules: bool = False

    def validate_fail_closed(self) -> bool:
        """Valida que ninguna regla no vigente se ejecute sin autorizacion explicita."""
        for rule in self.rules:
            if rule.status != RegulatoryStatus.VIGENTE and not self.allow_experimental_rules:
                raise ValueError(
                    f"Regla '{rule.rule_id}' ({rule.description}) esta en estado '{rule.status.value}' "
                    f"y no puede ejecutarse en modo productivo sin 'allow_experimental_rules=True'."
                )
        return True

def get_standard_rules(inst_type: InstallationType) -> List[RegulatoryRule]:
    if inst_type == InstallationType.UTILITY_SSCC:
        return [
            RegulatoryRule(
                rule_id="NTSYCS-FFR-01",
                description="Respuesta rapida de frecuencia contingente (<500ms)",
                norm_reference="NTSyCS Anexo Tecnico Control de Frecuencia",
                status=RegulatoryStatus.VIGENTE,
                min_soc_reserve_pct=30.0,
            ),
            RegulatoryRule(
                rule_id="NTSYCS-VV-01",
                description="Soporte dinamico Volt/VAR en subestacion",
                norm_reference="NTSyCS Control de Tension",
                status=RegulatoryStatus.VIGENTE,
                min_soc_reserve_pct=10.0,
            ),
        ]
    elif inst_type == InstallationType.GENERATOR_FIRM:
        return [
            RegulatoryRule(
                rule_id="LEY21505-FIRM-01",
                description="Inyeccion garantizada en bloque crepuscular/nocturno",
                norm_reference="Ley 21.505 Almacenamiento y Electromovilidad",
                status=RegulatoryStatus.VIGENTE,
                min_soc_reserve_pct=50.0,
            ),
        ]
    elif inst_type == InstallationType.BTM_PEAK_SHAVING:
        return [
            RegulatoryRule(
                rule_id="DS11T-PEAK-01",
                description="Control de demanda maxima en horas de punta ST/T (18-22h)",
                norm_reference="Decreto Supremo N° 11T CNE",
                status=RegulatoryStatus.VIGENTE,
                requires_site_meter=True,
                min_soc_reserve_pct=15.0,
            ),
            RegulatoryRule(
                rule_id="SEC-ZERO-EXPORT-01",
                description="Inyeccion cero hacia alimentador de distribucion sin PMGD",
                norm_reference="Norma Tecnica de Distribucion / Pliego SEC",
                status=RegulatoryStatus.VIGENTE,
                requires_site_meter=True,
                min_soc_reserve_pct=10.0,
            ),
        ]
    elif inst_type == InstallationType.FREE_CLIENT_ARBITRAGE:
        return [
            RegulatoryRule(
                rule_id="PPA-ARBITRAGE-01",
                description="Arbitraje de bloques horarios de compra de energia",
                norm_reference="Contratos privados Cliente Libre / LGSE",
                status=RegulatoryStatus.VIGENTE,
                requires_site_meter=True,
                min_soc_reserve_pct=10.0,
            ),
            RegulatoryRule(
                rule_id="BTM-GRID-SUPPORT-EXP",
                description="Soporte a la red de distribucion / alivio de congestion BTM",
                norm_reference="Propuesta Regulatoria Flexibilidad CNE",
                status=RegulatoryStatus.EN_EVALUACION,
                min_soc_reserve_pct=25.0,
            ),
        ]
    return []
