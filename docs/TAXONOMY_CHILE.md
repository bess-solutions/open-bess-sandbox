# Taxonomía Regulatoria y Operativa de BESS en Chile

Este documento establece la **matriz formal de contextos de instalación para sistemas de almacenamiento de energía en baterías (BESS) en Chile**, sirviendo de base conceptual y técnica para la suite **Open BESS Edge** y el orquestador nacional **BESSAI**.

---

## 1. El Problema de Fondo: Ausencia de Contexto

Un equipo físico de almacenamiento (inversor/PCS + racks de celdas electroquímicas + BMS) opera de forma radicalmente distinta según el **rol y objetivo de su instalación**. Tratar cualquier batería como un nodo genérico de respuesta en frecuencia NTSyCS asume un solo contexto (Utility Transmisión) y genera incompatibilidades críticas cuando el sistema se instala en un cliente industrial o en una central híbrida.

Para resolver esto sin perder universalidad, la arquitectura desacopla:
1. **Mecanismos Invariables (Core Safety)**: Envolvente física de seguridad (*fail-closed* BESS-GUARD), limitador de hardware y auditoría inmutable.
2. **Contexto Declarativo (installation)**: Quién manda la consigna, qué objetivos se persiguen, qué señales de medición de campo se requieren y cuál es el marco regulatorio aplicable.

---

## 2. Matriz Comparativa de los 4 Contextos Clave

| Dimensión | 1. Utility-Scale SSCC | 2. Respaldo de Generación | 3. Peak Shaving BTM | 4. Cliente Libre Arbitraje |
|---|---|---|---|---|
| **Punto de Conexión** | Subestación Transmisión / Subtransmisión | Barra de Central de Generación (Híbrida) | Tablero General / Frontera Industrial | Empalme Cliente Libre (BTM o dedicado) |
| **Quién comanda consignas** | Coordinador Eléctrico Nacional (CEN / SITR) | Operador Central + Despacho Económico CEN | EMS Local / Algoritmo de Demanda | BESSAI Optimizer / Agente de Mercado |
| **Objetivo Operativo** | Inercia sintética, FFR, CPF y control de tensión | Evitar vertimiento (curtailment) e inyección nocturna | Reducir demanda máxima en horas de punta | Minimizar costo de compra de energía ($/MWh) |
| **Mediciones Requeridas** | $ (Hz), $ (kV) en barra; $, $ de planta | Generación bruta ERNC, capacidad de línea de evacuación | **Medidor de Carga de Fábrica ({load}, Q_{load}$)** | Medidor de consumo + Señal horaria de tarifa |
| **Lazos de Control Activos** | FFR Droop (rápido) + Volt/VAR NTSyCS | Seguidor de rampa + Rellenado de valles (Peak Shift) | Recorte de demanda sobre umbral ({grid} \le P_{cap}$) | Despacho programado / Optimizador de precios |
| **Reserva de SOC** | Reserva dinámica simétrica (~50% o según SSCC) | Reserva alta previa a bloque de inyección programada | SOC alto antes de las 18:00 h (inicio punta) | SOC flexible según curva horaria de precios |
| **Estado Regulatorio en Código** | **SUPUESTO** (NTSYCS-FFR-01 / NTSYCS-VV-01) | **SUPUESTO** (LEY21505-FIRM-01 / NTCO-ZERO-EXPORT-01) | **SUPUESTO** (TARIFF-PEAK-01: Art. 182° LGSE / PNP) | **SUPUESTO / EN_EVALUACION** (PPA-ARBITRAGE-01 / BTM-FLEX-01) |

---

## 3. Especificación Detallada por Contexto

### Contexto 1: Utility-Scale Transmisión (SSCC NTSyCS)
- **Marco Normativo**: NTSyCS (Norma Técnica de Seguridad y Calidad de Servicio), Anexo Técnico Control de Frecuencia y Tensión, Resolución Exenta CNE.
- **Autoridad de Mando**: Coordinador Eléctrico Nacional (CEN).
- **Obligaciones de Control**:
  - Respuesta Rápida en Frecuencia (FFR) sub-500 ms ante contingencias ( < 49.80$ Hz o  > 50.20$ Hz).
  - Control Primario de Frecuencia (CPF) proporcional sin offset de reposición sin autorización.
  - Soporte de potencia reactiva Volt/VAR dinámico en el punto de conexión.
- **Regla Fail-Closed**: Si se pierde enlace con el SITR del CEN por más del watchdog permitido, el nodo transiciona a modo autónomo local conservando estatismo fijo sin saturar la red.

### Contexto 2: Respaldo y Co-localización en Generación (Solar/Eólica + BESS)
- **Marco Normativo**: Ley N° 21.505 de Almacenamiento y Electromovilidad, Norma Técnica de Conexión de Generación.
- **Autoridad de Mando**: Operador de la central generadora en coordinación con el programa de despacho del CEN.
- **Obligaciones de Control**:
  - Carga activa de excedentes de generación renovable durante horas de congestión o precio cero.
  - Descarga controlada en bloque nocturno/crepúsculo respetando la capacidad máxima de evacuación en la subestación común.
  - Coordinación con el inversor solar para evitar desconexiones por sobretensión en barra interna.
- **Gestión de SOC**: La reserva de energía no se descarga aleatoriamente durante el día; se preserva para el bloque contractual comprometido.

### Contexto 3: Detrás del Medidor (Behind-The-Meter, BTM Industrial - Peak Shaving)
- **Marco Normativo**: Art. 182° Ley General de Servicios Eléctricos (LGSE), Decretos semestrales de Precios de Nudo Promedio (PNP) de la CNE y Decretos de Fórmulas Tarifarias de Distribución (horas punta 18:00–22:00 de abril a septiembre).
- **Autoridad de Mando**: EMS local del cliente o agente de optimización edge.
- **Obligaciones de Control**:
  - **Medidor Externo Obligatorio**: Requiere lectura en tiempo real del medidor de carga general de la planta industrial ({load}$).
  - Algoritmo de rasurado de picos:
    P_{bess}(t) = \max(0, P_{load}(t) - P_{cap})
    donde {cap}$ es la meta de potencia contratada en horas de punta (18:00 - 22:00 hrs en período de control).
  - **Inyección Cero**: A menos que la instalación cuente con autorización de inyección (e.g. Net Billing o PMGD BTM), {bess}(t) \le P_{load}(t)$ para prevenir inyección inversa hacia el alimentador de distribución.

### Contexto 4: Cliente Libre (Arbitraje y Eficiencia Energética)
- **Marco Normativo**: Ley General de Servicios Eléctricos (LGSE), contratos privados de suministro PPA, marco emergente de agregación y flexibilidad BTM.
- **Autoridad de Mando**: Orquestador BESSAI / Gestor de Energía del cliente.
- **Obligaciones de Control**:
  - Cargar en bloques de menor costo marginal o solar y descargar para desplazar compras en bloques caros.
  - Co-optimización de degradación electroquímica (costo nivelado de almacenamiento, LCOS) versus beneficio económico por spread tarifario.
  - Modo Isla / Backup ante interrupciones de suministro en la red pública.

---

## 4. Principio de Seguridad Regulatoria: Fail-Closed para Reglas

1. Si una regla o servicio está en estado **en_evaluacion** (como el apoyo a la transmisión BTM o SSCC descentralizados en Chile), el software no permite ejecutarla en modo autónomo vinculante sin una directiva explícita (llow_experimental_regulatory_modes: true).
2. Una hipótesis comercial o contractual nunca puede vulnerar los límites de la envolvente de seguridad de hardware (BESS-GUARD).
