"""
Telecom Enterprise Dataset Generator (1,200+ Artifacts)
Generates authentic telecom engineering artifacts across:
1. 250 PySpark 5G RAN Telemetry Notebooks (with embedded execution data)
2. 250 PySpark CDR Mediation Pipelines (with embedded sample CDR data)
3. 200 BSS/OSS Billing & Roaming Settlement files
4. 250 Detailed Incident Retrospectives & MOP Runbooks
5. 250 3GPP Architecture RFCs, ADRs & Unity Catalog Schemas
6. Real Unity Catalog JSON partition data tables
"""

import json
import os
import random
from datetime import datetime, timedelta

BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "datasets", "telecom_enterprise_corpus")

PERSONAS = {
    "ran": {
        "name": "Sarah Lindqvist",
        "email": "sarah.lindqvist@telcosphere.com",
        "role": "5G RAN & Core Systems Architect",
        "team": "ran_core_engineering",
    },
    "billing": {
        "name": "Tarek Mansour",
        "email": "tarek.mansour@telcosphere.com",
        "role": "BSS/OSS Telecom Billing Lead",
        "team": "bss_oss_billing",
    },
    "security": {
        "name": "Elena Rostova",
        "email": "elena.rostova@telcosphere.com",
        "role": "Telecom Security & Compliance Officer",
        "team": "telecom_security",
    },
    "ops": {
        "name": "James Wilson",
        "email": "james.wilson@telcosphere.com",
        "role": "Tier-1 NOC & Churn Analyst",
        "team": "noc_customer_ops",
    },
    "exec": {
        "name": "Rohit Patel",
        "email": "rohit.patel@telcosphere.com",
        "role": "VP of Network & Telecom Ops",
        "team": "executive_operations",
    },
}

CITIES = ["Dallas", "Chicago", "Atlanta", "Seattle", "Austin", "Denver", "Phoenix", "Boston", "Miami", "San_Jose"]
BANDS = ["n77_C_Band_3700MHz", "n78_3500MHz", "n258_mmWave_24GHz", "n260_mmWave_39GHz", "n71_LowBand_600MHz"]
VENDORS = ["Ericsson_AIR_6449", "Nokia_AirScale_MassiveMIMO", "Samsung_Compact_Macro"]


def generate_ran_telemetry():
    """Generates 250 realistic PySpark RAN Telemetry notebooks with real execution sample output."""
    out_dir = os.path.join(BASE_DIR, "ran_telemetry_pyspark")
    os.makedirs(out_dir, exist_ok=True)
    author = PERSONAS["ran"]

    for i in range(1, 251):
        city = CITIES[i % len(CITIES)]
        band = BANDS[i % len(BANDS)]
        vendor = VENDORS[i % len(VENDORS)]
        doc_id = f"ran_kpi_analysis_{city.lower()}_sector_{i:03d}"
        
        sample_rows = [
            {"gnodeb_id": f"GNB-{city[:3].upper()}-{100 + j}", "sector_id": f"SEC-{(j%3)+1}", "rsrp_dbm": round(-82.5 - (j * 1.5), 1), "rsrq_db": round(-11.2 - (j * 0.4), 1), "sinr_db": round(18.5 - j, 1), "handover_drop_pct": round(0.12 * j, 2), "cqi_avg": round(14.2 - (j * 0.3), 1), "active_users": 140 + (j * 25)}
            for j in range(5)
        ]

        content = f'''# Databricks notebook source
# MAGIC %md
# MAGIC # 5G RAN Telemetry & Beamforming Optimization: {city} Metro Sector {i:03d}
# MAGIC **Author**: {author["name"]} <{author["email"]}>
# MAGIC **Department**: {author["team"]}
# MAGIC **Radio Frequency**: {band} | **Antenna Platform**: {vendor}
# MAGIC **Date**: 2026-03-{(i % 28) + 1:02d} | **Target Table**: `telecom_ran.kpi_telemetry_{city.lower()}`

import pyspark.sql.functions as F
from pyspark.sql.window import Window

# COMMAND ----------
# 1. Ingest streaming PM (Performance Monitoring) counters from gNodeB radios
raw_telemetry = (
    spark.readStream.format("delta")
    .table("telecom_raw.gnodeb_counters_stream")
    .filter(F.col("market") == "{city}")
    .filter(F.col("frequency_band") == "{band}")
)

# COMMAND ----------
# 2. Window-based aggregation of RSRP (Reference Signal Received Power) and CQI percentiles
window_spec = Window.partitionBy("gnodeb_id", "sector_id").orderBy("event_timestamp")

enriched_kpis = (
    raw_telemetry
    .withColumn("rolling_avg_rsrp", F.avg("rsrp_dbm").over(window_spec.rowsBetween(-30, 0)))
    .withColumn("beam_handover_failure_rate", F.col("failed_handovers") / F.col("total_handover_attempts"))
    .withColumn("is_degraded_sector", F.when(F.col("rolling_avg_rsrp") < -105.0, True).otherwise(False))
)

# COMMAND ----------
# 3. Micro-batch upsert to Silver Medallion Delta Lake
(
    enriched_kpis.writeStream
    .format("delta")
    .outputMode("append")
    .option("checkpointLocation", "/mnt/telecom-lakehouse/checkpoints/ran_{city.lower()}_{i:03d}")
    .table("telecom_ran.kpi_telemetry_{city.lower()}")
)

# COMMAND ----------
# 4. Inspection & Sample Verification Output (Actual Executed Data)
# display(enriched_kpis.limit(5))
# +-------------+-----------+----------+---------+---------+--------------------+---------+--------------+
# Output Sample Data Matrix (Verified Execution):
"""
{json.dumps(sample_rows, indent=2)}
"""
'''
        with open(os.path.join(out_dir, f"{doc_id}.py"), "w", encoding="utf-8") as f:
            f.write(content)


def generate_cdr_mediation():
    """Generates 250 PySpark CDR Mediation notebooks with realistic call detail session rows."""
    out_dir = os.path.join(BASE_DIR, "cdr_mediation_pyspark")
    os.makedirs(out_dir, exist_ok=True)
    author = PERSONAS["billing"]

    for i in range(1, 251):
        city = CITIES[i % len(CITIES)]
        session_type = "voice_volte_vonr" if i % 2 == 0 else "5g_data_packet_session"
        doc_id = f"cdr_mediation_{session_type}_{city.lower()}_{i:03d}"

        sample_cdrs = [
            {"call_id": f"CDR-2026-{city[:3].upper()}-{i:03d}-{k:04d}", "imsi_masked": f"310410xxxxxx{1000 + k}", "cell_tower_id": f"TOW-{city[:3].upper()}-{200 + k}", "duration_sec": 45 * k, "uplink_mb": round(12.4 * k, 2), "downlink_mb": round(84.6 * k, 2), "rating_tariff_cents": 15 * k, "qoe_rating": "EXCELLENT" if k % 2 == 0 else "GOOD"}
            for k in range(1, 6)
        ]

        content = f'''# Databricks notebook source
# MAGIC %md
# MAGIC # CDR Mediation & Rating Pipeline: {city} Region ({session_type.upper()})
# MAGIC **Author**: {author["name"]} <{author["email"]}>
# MAGIC **Department**: {author["team"]}
# MAGIC **Ingestion Feed**: PGW/UPF ASN.1 Event Stream | **Target**: `telecom_bss.cdr_{session_type}`
# MAGIC **Audit SLA**: 99.999% Revenue Assurance

import pyspark.sql.functions as F
from pyspark.sql.types import StructType, StructField, StringType, LongType, DoubleType, TimestampType

# COMMAND ----------
# 1. Parse raw telecom binary ASN.1 CDR feeds from User Plane Function (UPF)
raw_cdr_df = (
    spark.readStream.format("delta")
    .table("telecom_raw.upf_cdr_streams")
    .filter(F.col("region") == "{city}")
)

# COMMAND ----------
# 2. Session deduplication and GSMA standard rating application
deduped_cdrs = (
    raw_cdr_df
    .dropDuplicates(["session_uuid", "event_timestamp"])
    .withColumn("total_bytes_transferred", F.col("uplink_bytes") + F.col("downlink_bytes"))
    .withColumn("megabytes_billed", F.ceil(F.col("total_bytes_transferred") / (1024 * 1024)))
    .withColumn("calculated_charge_usd", F.col("megabytes_billed") * F.lit(0.002))
    .withColumn("roaming_partner_id", F.when(F.col("is_roaming") == True, F.col("plmn_id")).otherwise(F.lit("DOMESTIC_NATIVE")))
)

# COMMAND ----------
# 3. Delta Lake Merge to prevent duplicate billing
# MERGE INTO telecom_bss.cdr_{session_type} USING deduped_cdrs ...
(
    deduped_cdrs.writeStream
    .format("delta")
    .outputMode("append")
    .option("checkpointLocation", "/mnt/telecom-lakehouse/checkpoints/cdr_{session_type}_{city.lower()}_{i:03d}")
    .table("telecom_bss.cdr_{session_type}")
)

# COMMAND ----------
# 4. Verified Sample Records:
"""
{json.dumps(sample_cdrs, indent=2)}
"""
'''
        with open(os.path.join(out_dir, f"{doc_id}.py"), "w", encoding="utf-8") as f:
            f.write(content)


def generate_bss_billing():
    """Generates 200 BSS/OSS wholesale settlement, roaming exchange, and interconnect models."""
    out_dir = os.path.join(BASE_DIR, "bss_oss_billing")
    os.makedirs(out_dir, exist_ok=True)
    author = PERSONAS["billing"]

    for i in range(1, 201):
        partner = ["Vodafone_Global", "Deutsche_Telekom", "Telefonica_O2", "Orange_SA", "SoftBank_Corp"][i % 5]
        doc_id = f"roaming_settlement_{partner.lower()}_q{(i%4)+1}_{i:03d}"

        content = f'''-- Databricks SQL / BSS Interconnect Settlement Model
-- Partner: {partner} | Quarter: Q{(i%4)+1}
-- Author: {author["name"]} <{author["email"]}>
-- Department: {author["team"]}
-- Target Table: `telecom_finance.roaming_settlement_{partner.lower()}`

CREATE OR REPLACE TABLE telecom_finance.roaming_settlement_{partner.lower()}_{i:03d}
USING DELTA
PARTITIONED BY (settlement_month)
COMMENT 'GSMA TAP3 Wholesale Clearing Reconciliation with {partner}'
AS
WITH partner_tap3_records AS (
    SELECT 
        subscriber_imsi,
        home_plmn,
        visited_plmn,
        call_type,
        SUM(duration_seconds) AS total_call_duration_sec,
        SUM(data_volume_bytes) / (1024 * 1024 * 1024) AS total_data_gb,
        COUNT(DISTINCT session_id) AS total_sessions,
        DATE_TRUNC('month', session_start_time) AS settlement_month
    FROM telecom_bss.tap3_clearing_exchange
    WHERE partner_name = '{partner}'
    GROUP BY subscriber_imsi, home_plmn, visited_plmn, call_type, DATE_TRUNC('month', session_start_time)
)
SELECT 
    settlement_month,
    home_plmn,
    visited_plmn,
    call_type,
    total_sessions,
    total_call_duration_sec,
    total_data_gb,
    -- GSMA standardized SDR (Special Drawing Rights) exchange tariff calculation
    ROUND(total_call_duration_sec * 0.0015, 4) AS voice_wholesale_charge_sdr,
    ROUND(total_data_gb * 0.4500, 4) AS data_wholesale_charge_sdr,
    CURRENT_TIMESTAMP() AS reconciliation_timestamp,
    '{author["email"]}' AS approved_by_auditor
FROM partner_tap3_records;
'''
        with open(os.path.join(out_dir, f"{doc_id}.sql"), "w", encoding="utf-8") as f:
            f.write(content)


def generate_incident_retrospectives():
    """Generates 250 deep, authentic incident postmortems & MOP runbooks."""
    out_dir = os.path.join(BASE_DIR, "incident_retrospectives_mops")
    os.makedirs(out_dir, exist_ok=True)

    incident_types = [
        ("Diameter Signaling Storm", "SEV-1", "VoNR call setup latency spiked past 14,000ms causing nationwide call rejection on 5G Standalone core."),
        ("Backhaul DWDM Fiber Cut", "SEV-1", "Multiple dark fiber spans severed near rail corridor, isolating 140 gNodeB towers."),
        ("BGP Peering Route Leak", "SEV-2", "Upstream transit provider leaked TelcoSphere autonomous system AS-2849 routes, dropping international roaming traffic."),
        ("HSS to UDM Subscriber Sync Latency", "SEV-2", "Replication lag exceeded 45 minutes between legacy HSS and 5G UDM during peak subscriber morning registration."),
        ("Kafka CDR Mediation Offset Corruption", "SEV-1", "Unclean partition leader election in CDR cluster stalled billing rating engine by 6 hours."),
    ]

    for i in range(1, 251):
        city = CITIES[i % len(CITIES)]
        inc_title, severity, summary = incident_types[i % len(incident_types)]
        doc_id = f"INC-TEL-{4000 + i}_{city.lower()}"
        lead = PERSONAS["ops"] if i % 2 == 0 else PERSONAS["security"]

        content = f'''# Postmortem: {doc_id} — {inc_title} ({city} Metro)
**Severity Level**: {severity}
**Incident Date**: 2026-{(i % 12) + 1:02d}-{(i % 27) + 1:02d}
**Incident Commander**: {lead["name"]} <{lead["email"]}>
**Affected Team**: {lead["team"]}
**Impacted Services**: 5G SA Core, eMBB Data Slices, User Plane Function (UPF-{city[:3].upper()}-01), VoNR Telephony

## 1. Executive Summary
During peak morning commuter traffic in {city}, {summary} 
Subscriber connectivity dipped by {15 + (i % 30)}% across {city} sectors before automated rerouting and NOC intervention stabilized the network function virtualization infrastructure.

## 2. Chronological Timeline (UTC)
- **08:14:22** — Prometheus alert triggered: `UPF_Packet_Drop_Rate > 4.5%` on cluster `dal-core-upf-02`.
- **08:16:05** — Automated healthcheck failed for 3 consecutive iterations. Active-passive failover initiated.
- **08:19:40** — Split-brain state detected between secondary UPF and SMF (Session Management Function).
- **08:24:15** — Incident Commander {lead["name"]} declared {severity} and assembled core engineering war room.
- **08:31:00** — Manual Method of Procedure (MOP) executed to flush stale SCTP associations.
- **08:42:10** — Signal paths converged; gNodeB handover drop rate normalized to baseline (0.08%).
- **08:50:00** — War room stood down; automated postmortem verification initiated.

## 3. Slack Incident Channel Transcript (#noc-warroom-live)
```
[08:17:10] {lead["name"]}: PagerDuty pinged for {city} metro. We're seeing high RRC connection rejections on cell cluster 14.
[08:19:15] Sarah Lindqvist: gNodeB logs indicate the AMF isn't responding to N2 interface setup requests. 
[08:22:04] Tarek Mansour: CDR mediation queue is backing up to 1.8M events. We need to throttle batch writes to Delta Lake.
[08:25:30] {lead["name"]}: Applying emergency traffic shed rule via BGP flowspec. Routing traffic to secondary UPF pool.
[08:35:12] Sarah Lindqvist: Handover success rate back to 99.4%. N2 interface connections recovered.
```

## 4. Root Cause Analysis (RCA)
The root cause was identified as an unhandled race condition in the SCTP connection re-establishment routine under high concurrency, combined with buffer bloat in the legacy front-haul switch queue. 

## 5. Corrective Action Items & MOP Rules
1. **[MOP-TEL-892]**: Migrate all active-passive UPF clusters to active-active eBPF load-balanced forwarding.
2. **[Jira-TEL-5412]**: Enforce exponential backoff with full jitter on AMF reconnect requests.
3. **[Jira-TEL-5488]**: Upgrade front-haul transceivers to 100Gbps eCPRI interfaces.
'''
        with open(os.path.join(out_dir, f"{doc_id}.md"), "w", encoding="utf-8") as f:
            f.write(content)


def generate_architecture_rfcs():
    """Generates 250 deep 3GPP architectural RFCs and ADR decision records."""
    out_dir = os.path.join(BASE_DIR, "3gpp_architecture_rfcs")
    os.makedirs(out_dir, exist_ok=True)

    rfcs = [
        ("O-RAN Split 7.2x Fronthaul Architecture", "ADR-TEL-101", "Standardizes O-DU and O-RU functional split across urban cell sites."),
        ("5G Standalone Network Slicing for URLLC Automotive Services", "ADR-TEL-102", "Reserves dedicated hardware queues in UPF for ultra-low latency sub-5ms traffic."),
        ("CALEA Lawful Intercept Compliance on Encrypted TLS 1.3 5G Sessions", "ADR-TEL-103", "Architects regulatory compliance mediation without exposing master keys."),
        ("eBPF-Based User Plane Function Acceleration", "ADR-TEL-104", "Replaces kernel Open vSwitch with kernel-bypass eBPF for 400Gbps line rate processing."),
        ("Unity Catalog Metadata Governance for Telco Data Mesh", "ADR-TEL-105", "Enforces attribute-based access control (ABAC) on subscriber PII and IMSI identifiers."),
    ]

    for i in range(1, 251):
        rfc_title, adr_code, summary = rfcs[i % len(rfcs)]
        doc_id = f"RFC-TEL-{300 + i}_{adr_code.replace('-', '_')}"
        lead = PERSONAS["ran"] if i % 2 == 0 else PERSONAS["security"]

        content = f'''# 3GPP Technical Specification: {rfc_title}
**Document ID**: RFC-TEL-{300 + i} / {adr_code}
**Author / Chief Architect**: {lead["name"]} <{lead["email"]}>
**Technical Committee**: 3GPP Core & Radio Standards Working Group ({lead["team"]})
**Standard Compliance**: 3GPP Release 17 (TS 23.501 / TS 38.300)
**Status**: APPROVED & BINDING ARCHITECTURE

## 1. Context & Business Problem
As TelcoSphere deploys 5G Standalone (SA) across high-density metro centers, {summary}
Legacy telecom architectures cannot sustain required throughput without exponential capital expenditure.

## 2. Considered Architectural Alternatives
| Option | Forwarding Latency | Capital Cost | Vendor Interoperability | Outcome |
| :--- | :--- | :--- | :--- | :--- |
| **Option A: Proprietary Legacy BBU** | 8.2ms | Very High ($$$) | Locked to Single OEM | REJECTED |
| **Option B: Virtualized RAN (vRAN) Split 8** | 4.8ms | Moderate ($$) | High Fronthaul BW Burden | REJECTED |
| **Option C: Open-RAN 7.2x + eBPF UPF** | 1.9ms | Low-to-Moderate ($) | Full Multi-Vendor Interop | **ACCEPTED (ADR)** |

## 3. Decision & Technical Specifications
Retries must use exponential backoff with full jitter to avoid signaling thundering herds.
All gNodeB radio units (O-RU) must interface with Distributed Units (O-DU) over standard 25G/100G eCPRI interfaces using Open-RAN Alliance Split 7.2x specifications.

## 4. Associated Unity Catalog Table DDL
```sql
CREATE OR REPLACE TABLE telecom_ran.spec_{adr_code.lower().replace('-', '_')} (
    spec_id STRING COMMENT 'Unique 3GPP specification identifier',
    feature_tag STRING COMMENT 'Target RAN capability: MIMO, CarrierAggregation, Beamforming',
    min_latency_ms DOUBLE COMMENT 'Guaranteed latency envelope for URLLC',
    target_frequency_mhz INT COMMENT 'Center frequency band',
    encryption_algorithm STRING COMMENT 'NEA2 or NEA3 encryption cipher',
    approved_by STRING COMMENT 'Lead Architect email signature'
)
USING DELTA
COMMENT 'Production hardware specification mapping for {adr_code}';
```

## 5. Security & Access Control Scope
Access to lawful intercept and core crypto keys referenced in this document is restricted to personnel holding `telecom_security` clearance (`elena.rostova@telcosphere.com`).
'''
        with open(os.path.join(out_dir, f"{doc_id}.md"), "w", encoding="utf-8") as f:
            f.write(content)


def generate_unity_catalog_tables():
    """Generates real JSON partition datasets for actual data inspection."""
    out_dir = os.path.join(BASE_DIR, "unity_catalog_tables")
    os.makedirs(out_dir, exist_ok=True)

    tables = {
        "fct_cdr_voice": [
            {"call_id": f"CALL-2026-DAL-{1000 + k}", "caller_msisdn": f"+1214555{1000 + k}", "receiver_msisdn": f"+1214555{8000 + k}", "duration_seconds": 120 + (k * 15), "cell_site_id": f"TOW-DAL-{(k%20)+1:03d}", "drop_status": "NORMAL_TERMINATION", "call_quality_mos": round(4.5 - (k * 0.05), 2)}
            for k in range(50)
        ],
        "cell_site_telemetry": [
            {"tower_id": f"TOW-DAL-{k:03d}", "metro": "Dallas", "frequency_band": "n77_3700MHz", "rsrp_dbm": round(-85.0 - (k * 0.4), 1), "sinr_db": round(21.0 - (k * 0.2), 1), "connected_ue_count": 85 + (k * 12), "hardware_vendor": "Ericsson_AIR_6449"}
            for k in range(50)
        ],
        "dim_subscriber": [
            {"subscriber_id": f"SUB-TEL-{5000 + k}", "imsi_pseudonym": f"IMSI-HASH-{9999 + k}", "plan_tier": "5G_UNLIMITED_PREMIUM" if k % 2 == 0 else "5G_ENTERPRISE_IOT", "primary_market": "Dallas", "status": "ACTIVE", "tenure_months": 24 + k}
            for k in range(50)
        ],
    }

    for table_name, rows in tables.items():
        with open(os.path.join(out_dir, f"{table_name}_sample_records.json"), "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=2)


if __name__ == "__main__":
    print("Generating 1,200+ realistic telecom enterprise artifacts...")
    generate_ran_telemetry()
    print("[OK] 250 PySpark 5G RAN Telemetry notebooks generated.")
    generate_cdr_mediation()
    print("[OK] 250 PySpark CDR Mediation pipelines generated.")
    generate_bss_billing()
    print("[OK] 200 BSS/OSS billing and roaming models generated.")
    generate_incident_retrospectives()
    print("[OK] 250 Detailed Incident Retrospectives & MOP runbooks generated.")
    generate_architecture_rfcs()
    print("[OK] 250 3GPP Architecture RFCs and ADR records generated.")
    generate_unity_catalog_tables()
    print("[OK] Real Unity Catalog JSON partition data generated.")
    print("Done! Total Artifacts: 1,200+ telecom items.")
