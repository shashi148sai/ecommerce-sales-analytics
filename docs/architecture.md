# SalesPulse Analytics - System Architecture & Engineering Design

## 1. High-Level Architecture Overview

SalesPulse Analytics integrates **Big Data Analytics (BDA)** and **Cloud Computing (CC)** into a single unified analytical pipeline. The architecture decouples distributed compute from durable object storage, enabling seamless transition between **₹0 local development** and **AWS Cloud infrastructure**.

```mermaid
flowchart TD
    subgraph INGESTION["1. Ingestion Layer"]
        RAW["Raw Dataset<br/>(UCI Online Retail: 541,909 rows)<br/>CSV / XLSX Format"]
        VAL["Schema Conformance & Validator<br/>(8 Mandatory Attributes, Type Bounds)"]
        DQR["Data Quality Auditor<br/>(Missing, Duplicates, Cancellations)"]
    end

    subgraph PROCESSING["2. Distributed Big Data Compute (Apache Spark 3.5)"]
        PYSPARK["PySpark Data Cleaning & Normalization<br/>- Identifier String Preservation<br/>- Temporal Parsing (Coalesce Date Patterns)<br/>- LineTotal = Quantity * UnitPrice"]
        SPLIT["Dataset Partitioning & Business Rule Engine"]
        MASTER["Cleaned Master DF<br/>(524,878 rows)"]
        SALES["Sales-Eligible DF<br/>(Quantity > 0, Price > 0)"]
        RETURNS["Returns & Cancellations DF<br/>(Invoice C* or Qty < 0)"]
    end

    subgraph ANALYTICS["3. Analytical Engine (Spark SQL & ML)"]
        SQL["Spark SQL In-Memory Views<br/>v_valid_sales, v_cancellations_returns"]
        KPIS["Commercial KPIs<br/>Gross/Net Sales, AOV, MoM Growth"]
        ML_TS["Time-Series Forecasting<br/>(Ridge Regularized + Hold-Out Validation)"]
        ML_RFM["RFM Customer Segmentation<br/>(Recency, Frequency, Monetary K-Means)"]
    end

    subgraph STORAGE["4. Hybrid Storage Layer"]
        SM["StorageManager Abstraction"]
        LOCAL["Local Disk Storage<br/>data/{raw, processed, analytics, reports, metadata}"]
        S3["Amazon S3 Cloud Storage<br/>s3://bucket/{raw, processed, analytics, reports, metadata}"]
    end

    subgraph PRESENTATION["5. Interactive Web Application (Streamlit)"]
        P1["1. Sales Overview"]
        P2["2. Product Analytics"]
        P3["3. Sales Trends"]
        P4["4. Customer & Regional"]
        P5["5. Data Management & S3"]
        P6["6. Forecasting & Segmentation"]
        P7["7. System Performance"]
    end

    RAW --> VAL --> DQR --> PYSPARK
    PYSPARK --> SPLIT
    SPLIT --> MASTER
    SPLIT --> SALES
    SPLIT --> RETURNS
    MASTER & SALES & RETURNS --> SQL
    SALES --> ML_TS & ML_RFM
    SQL --> KPIS
    KPIS & ML_TS & ML_RFM --> SM
    SM --> LOCAL
    SM -. Optional Cloud Replication .-> S3
    LOCAL --> PRESENTATION
```

---

## 2. Key Architecture Pillars

### Decoupled Storage and Compute
- **Compute Layer**: Apache Spark (via PySpark 3.5) runs compute workloads in-memory. In local mode, JVM workers run on allocated cores (`local[2]`), while in cloud mode, the identical PySpark codebase runs on AWS EMR (Elastic MapReduce) or an EC2 cluster.
- **Storage Layer**: Transparent persistence abstracted by `StorageManager`. Files are stored under standard prefixes:
  - `raw/`: Immutable source transactional logs.
  - `processed/`: Cleansed, strongly-typed Parquet and CSV files.
  - `analytics/`: Summary aggregation tables for sub-second dashboard rendering.
  - `reports/`: Data quality audit JSON/CSV reports.
  - `metadata/`: Execution telemetry (durations, throughput, memory).

### Zero-Fabrication Integrity Policy
- **Currency**: Transactions originate from a UK-based retailer in Great Britain Pounds (£). No silent conversions to INR or USD are performed.
- **Financial Metrics**:
  $$\text{Gross Sales} = \sum (\text{Quantity} \times \text{UnitPrice}) \quad \forall \text{ valid sales}$$
  $$\text{Return Adjustments} = \left| \sum (\text{Quantity} \times \text{UnitPrice}) \right| \quad \forall \text{ cancellations/refunds}$$
  $$\text{Net Sales} = \text{Gross Sales} - \text{Return Adjustments}$$
- **Profit Disclaimer**: Since Cost of Goods Sold (COGS) is absent in the UCI dataset, profit margins are explicitly **not** claimed.
