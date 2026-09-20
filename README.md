# Open BESS Sandbox — Laboratorio Multicontexto y Banco de Pruebas

[![CI](https://github.com/bess-solutions/open-bess-sandbox/actions/workflows/ci.yml/badge.svg)](https://github.com/bess-solutions/open-bess-sandbox/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/)

Repositorio de investigación, pruebas de concepto y simulación multicontexto para sistemas de almacenamiento de energía en baterías (**BESS**) en Chile, parte del ecosistema abierto de **BESS Solutions** y la plataforma nacional **BESSAI**.

---

## 💡 El Problema: El BESS no sabe para qué está instalado

Un mismo equipo físico (PCS + Batería) se comporta de forma radicalmente distinta según su **rol operativo**. Si el software asume un único contexto (e.g. respuesta en frecuencia NTSyCS en transmisión), falla ante clientes industriales que requieren *peak shaving* o centrales renovables que necesitan mitigar vertimientos.

Este sandbox evalúa y demuestra la **arquitectura en tres capas**:
1. **Mecanismos Invariables (Core Safety)**: Envolvente física de seguridad (*fail-closed*), limitador físico y auditoría inmutable (probados en `open-bess-edge` v3.0).
2. **Contexto Declarativo (`installation`)**: Quién comanda (CEN, Operador, EMS, BESSAI), qué objetivos persigue y qué medidores externos requiere.
3. **Reglas Regulatorias con Seguridad Fail-Closed**: Cada regla lleva su estado (`vigente`, `en_evaluacion`, `supuesto`). Si una regla está *en evaluación*, el sistema no opera sin autorización explícita.

---

## ⚡ Los 4 Contextos Clave en Chile

Consulta la especificación completa en [docs/TAXONOMY_CHILE.md](docs/TAXONOMY_CHILE.md).

| Contexto | Quién comanda | Objetivo Primario | Medición Requerida | Estado Regulatorio |
|---|---|---|---|---|
| **1. Utility-Scale SSCC** | Coordinador Eléctrico Nacional (CEN) | FFR sub-500ms + Volt/VAR | $f, V$ en subestación | **Vigente** (NTSyCS) |
| **2. Respaldo Generación** | Operador Central + Despacho CEN | Mitigar vertimiento solar e inyectar de noche | Medidor de generación solar bruta | **Vigente** (Ley 21.505) |
| **3. Peak Shaving BTM** | EMS Cliente Industrial / BESSAI | Recortar demanda en horas punta (18-22h) | **Medidor de Carga de Fábrica ($P_{load}$)** | **Vigente** (DS 11T / 8T) |
| **4. Cliente Libre Arbitraje** | Orquestador BESSAI / Cliente | Arbitraje horario de compra de energía | Medidor de consumo + Tarifa horaria | **Mixto** (PPA vigente / Flexibilidad en eval.) |

---

## 🚀 Ejecución de Simulación Comparativa en Paralelo

Para ejecutar los 4 escenarios simultáneamente y comparar métricas de despacho, energía y cumplimiento:

```bash
python -m open_bess_sandbox.compare_runner
```

### Salida Esperada

```text
================================================================================
OPEN BESS SANDBOX — RESULTADOS COMPARATIVOS MULTICONTEXTO EN PARALELO
================================================================================
| Contexto Operativo | Descarga (kWh) | Carga (kWh) | Indicador Clave (KPI) | Fugas de Seguridad | Conformidad |
|---|---|---|---|---|---|
| **btm_peak_shaving** | 632.1 | 0.0 | Recorte Máximo Demanda: **350.0 kW reducidos en punta** | 0 | 100% |
| **free_client_arbitrage** | 720.0 | 800.0 | Margen Neto Arbitraje: **67.20 USD/día** | 0 | 100% |
| **generator_firm** | 1500.0 | 1850.0 | Vertimiento Renovable Evitado: **1850.0 kWh mitigados** | 0 | 100% |
| **utility_sscc** | 0.59 | 0.0 | Respuesta Contingente FFR: **214.3 kW (<500ms)** | 0 | 100% |
================================================================================
```

---

## 🧪 Pruebas Unitarias y de Integración

```bash
pytest tests/
```

---

## 📜 Licencia

Licencia Apache-2.0. Desarrollado por [BESS Solutions](https://bess-solutions.cl).
