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
    legal_basis: str
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
        """Valida que ninguna regla que sea SUPUESTO o EN_EVALUACION se ejecute sin autorizacion explicita."""
        for rule in self.rules:
            if rule.status != RegulatoryStatus.VIGENTE and not self.allow_experimental_rules:
                raise ValueError(
                    f"Regla '{rule.rule_id}' ({rule.description}) esta en estado '{rule.status.value}' "
                    f"segun {rule.legal_basis}. No puede ejecutarse en modo productivo sin 'allow_experimental_rules=True'."
                )
        return True

def get_standard_rules(inst_type: InstallationType) -> List[RegulatoryRule]:
    if inst_type == InstallationType.UTILITY_SSCC:
        return [
            RegulatoryRule(
                rule_id="NTSYCS-FFR-01",
                description="Respuesta rapida de frecuencia contingente (<500ms)",
                norm_reference="NTSyCS Anexo Tecnico Control de Frecuencia",
                legal_basis="Resolucion Exenta CNE N° 151/2020 modificada, Capitulo 5 (Reserva Primaria de Frecuencia)",
                status=RegulatoryStatus.VIGENTE,
                min_soc_reserve_pct=30.0,
            ),
            RegulatoryRule(
                rule_id="NTSYCS-VV-01",
                description="Soporte dinamico Volt/VAR en barra de conexion",
                norm_reference="NTSyCS Control de Tension y Potencia Reactiva",
                legal_basis="Resolucion Exenta CNE N° 151/2020, Capitulo 3, Art. 3-8",
                status=RegulatoryStatus.VIGENTE,
                min_soc_reserve_pct=10.0,
            ),
        ]
    elif inst_type == InstallationType.GENERATOR_FIRM:
        return [
            RegulatoryRule(
                rule_id="LEY21505-FIRM-01",
                description="Inyeccion garantizada en bloque crepuscular/nocturno para suficiencia de potencia",
                norm_reference="Ley N° 21.505 de Almacenamiento y Electromovilidad",
                legal_basis="Ley 21.505 (DO 21.11.2022), modifica Art. 149° bis de la Ley General de Servicios Electricos (LGSE)",
                status=RegulatoryStatus.VIGENTE,
                min_soc_reserve_pct=50.0,
            ),
        ]
    elif inst_type == InstallationType.BTM_PEAK_SHAVING:
        return [
            RegulatoryRule(
                rule_id="TARIFF-PEAK-01",
                description="Control y recorte de demanda maxima leida en horas de punta del sistema (18:00 a 22:00 hrs)",
                norm_reference="Tarifas de Suministro Electrico / Cargos por Potencia de Punta (LGSE Art. 182)",
                legal_basis="Decretos de Formulas Tarifarias de Distribucion y Precios de Nudo Promedio (PNP) CNE (Horas de punta abril-septiembre)",
                status=RegulatoryStatus.VIGENTE,
                requires_site_meter=True,
                min_soc_reserve_pct=15.0,
            ),
            RegulatoryRule(
                rule_id="NTCO-ZERO-EXPORT-01",
                description="Inyeccion cero hacia la red de distribucion en modo autoconsumo sin contrato PMGD",
                norm_reference="Norma Tecnica de Conexion y Operacion de PMGD / Pliego Tecnico Normativo RPTD",
                legal_basis="Res. Ex. CNE N° 166 y Pliegos RPTD N° 01 a 15 de la Superintendencia de Electricidad y Combustibles (SEC)",
                status=RegulatoryStatus.VIGENTE,
                requires_site_meter=True,
                min_soc_reserve_pct=10.0,
            ),
        ]
    elif inst_type == InstallationType.FREE_CLIENT_ARBITRAGE:
        return [
            RegulatoryRule(
                rule_id="PPA-ARBITRAGE-01",
                description="Arbitraje de bloques horarios de compra de energia segun contrato de suministro libre",
                norm_reference="Contratos Privados Bilaterales de Suministro (PPA) / LGSE Art. 147",
                legal_basis="Acuerdo comercial privado no mandatado por norma tecnica del CEN (Supuesto de Mercado)",
                status=RegulatoryStatus.SUPUESTO,
                requires_site_meter=True,
                min_soc_reserve_pct=10.0,
            ),
            RegulatoryRule(
                rule_id="BTM-GRID-SUPPORT-EXP",
                description="Soporte y alivio de congestion local en redes de distribucion BTM remunerado",
                norm_reference="Propuesta Reglamentaria de Flexibilidad y Servicios de Red CNE",
                legal_basis="Agenda Regulatoria CNE 2024-2026 (En proceso de consulta y tramitacion reglamentaria)",
                status=RegulatoryStatus.EN_EVALUACION,
                min_soc_reserve_pct=25.0,
            ),
        ]
    return []
