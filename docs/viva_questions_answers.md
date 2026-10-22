# SalesPulse Analytics - B.Tech Viva Questions & Comprehensive Answers
## Big Data Analytics (BDA) & Cloud Computing (CC) Project Defense

---

### Q1: What is the primary objective of this project?
**Answer:** The project builds an integrated enterprise analytics application named **SalesPulse Analytics** that combines Big Data Analytics and Cloud Computing into one system. It ingests 541,909 e-commerce transactions from the UCI Online Retail dataset, executes distributed data cleansing and Spark SQL aggregations using Apache Spark / PySpark, persists structured artifacts to local disk or Amazon S3 under logical prefixes, and renders an interactive 7-page analytical dashboard using Streamlit and Plotly.

---

### Q2: Why did you choose Apache Spark rather than traditional Pandas or SQL databases?
**Answer:** While Pandas operates strictly in a single-threaded Python runtime constrained by available RAM, Apache Spark provides:
1. **Distributed in-memory computing**: Divides datasets across partitions for parallel processing.
2. **Catalyst Query Optimizer**: Automatically optimizes logical execution plans, performs predicate pushdowns, and optimizes projection columns.
3. **Decoupled horizontal scalability**: The exact same PySpark codebase that runs locally in `local[2]` mode can execute on a 50-node AWS EMR cluster on terabytes of transactional logs without modifying the business logic.

---

### Q3: Did you run a real multi-node Spark cluster or local Spark?
**Answer:** In accordance with technical accuracy and hardware constraints, the application runs PySpark in **local standalone mode** (`local[2]`, utilizing 2 JVM executor threads and 2 GB allocated heap memory). We do not claim this single-machine execution is a distributed multi-node cluster, but the code adheres to distributed DataFrame and Spark SQL standards ready for multi-node deployment.

---

### Q4: What is the exact size and schema of the dataset used?
**Answer:** We used the canonical **UCI Online Retail dataset** containing **541,909 records** and 8 raw fields:
- `InvoiceNo` (String, with prefix 'C' for cancellations)
- `StockCode` (String, alphanumeric product identifier)
- `Description` (String, product description)
- `Quantity` (Integer, negative for returns)
- `InvoiceDate` (Timestamp/String, in format `dd-MM-yyyy HH:mm`)
- `UnitPrice` (Double, product price in GBP £)
- `CustomerID` (String, customer identifier)
- `Country` (String, customer country)

---

### Q5: How did you handle cancellations and returns?
**Answer:** A transaction is classified as a cancellation or return if `InvoiceNo` starts with `'C'` or `'c'` or if `Quantity < 0`. 
- In the UCI dataset, there are **9,288 cancellation records** and **10,624 negative quantity rows**.
- We separated transactions into two distinct subsets:
  1. **Sales-Eligible Dataset** (`Quantity > 0` and `UnitPrice > 0`): Used for computing Gross Revenue, Units Sold, and Average Order Value (AOV).
  2. **Returns & Adjustments Dataset**: Used to compute total refunded amounts and return rate percentages without distorting sales volume.

---

### Q6: What are Gross Sales, Return Adjustments, and Net Sales in your project?
**Answer:**
- **Gross Sales (£10,642,110.80)**: The sum of `Quantity * UnitPrice` across all valid, non-cancelled commercial transactions.
- **Return Adjustments (£893,979.73)**: The absolute sum of `Quantity * UnitPrice` across all cancellation and return entries.
- **Net Sales (£9,748,131.07)**: Computed as `Gross Sales - Return Adjustments`.

---

### Q7: Why does your application not display Profit Margins or Net Profit?
**Answer:** The UCI Online Retail dataset provides only `UnitPrice` (the retail selling price) and lacks Cost of Goods Sold (COGS) or supplier acquisition costs. In accordance with data science integrity standards, claiming profit analysis without cost figures would be fabricating numbers.

---

### Q8: What default currency is used and why?
**Answer:** The dataset was collected from a UK-based online gifts retailer. All transactions are denominated in **Great Britain Pounds (£ / GBP)**. We preserved £ throughout the application and did not silently convert to INR or USD to maintain currency precision.

---

### Q9: How did you handle missing CustomerID values?
**Answer:** There are **135,080 rows** where `CustomerID` is null or unassigned. In e-commerce, these represent **guest checkouts**. 
- In general sales and revenue aggregations, guest checkout rows are retained because real revenue was collected.
- In customer loyalty and RFM segmentation, we filter for registered customers or distinguish guest revenue (£1.7M) from registered customer revenue (£8.9M).
- `CustomerID` is strictly preserved as a formatted string (`"17850"` instead of `"17850.0"`).

---

### Q10: How did you solve the Windows PySpark winutils / hadoop.dll limitation?
**Answer:** When PySpark writes files locally on Windows, native Hadoop FileFormatWriter attempts to call `winutils.exe` and `hadoop.dll` to manage POSIX file permissions. To ensure 100% portability and prevent JVM crashes on any student or examiner machine:
- Distributed transformations, filtering, and Spark SQL aggregations run purely in Apache Spark.
- Final table exports to Parquet and CSV in our `StorageManager` utilize PyArrow and Pandas serializes with snappy compression.
- This produces standard Parquet and CSV files without requiring manual Hadoop installation.

---

### Q11: Explain your Cloud Computing integration with Amazon S3.
**Answer:** We implemented a unified `StorageManager` that abstracts persistence across local filesystem and Amazon S3. 
- S3 objects are organized under 5 enterprise logical prefixes: `raw/`, `processed/`, `analytics/`, `reports/`, and `metadata/`.
- S3 bucket is private with Server-Side Encryption (`AES256`).
- Uses `boto3` with automated exception handling (`NoCredentialsError`, `ClientError 403/404`) so the project runs ₹0 offline if no AWS credentials are provided.

---

### Q12: How did you ensure ₹0 out-of-pocket AWS costs?
**Answer:**
1. **Local Development First**: Full pipeline, testing, and Streamlit dashboard run 100% offline without AWS.
2. **AWS Free Tier Strict Alignment**: S3 storage consumption is under 100 MB (well below the 5 GB free tier limit).
3. **No Paid Managed Services**: Multi-node EMR clusters, RDS databases, and paid API gateways were intentionally avoided.
4. **Mocked Unit Tests**: Automated test suites use `unittest.mock` to verify S3 operations without making live network calls or incurring charges.

---

### Q13: What machine learning models are implemented in the project?
**Answer:**
1. **Time-Series Sales Demand Forecasting**: Uses regularized Ridge regression with calendar features (day of week, day of month) and autoregressive lags (Lag-1, Lag-7, 7-day rolling mean). It projects 30-day future demand with 95% confidence intervals and is evaluated on a chronological hold-out test set (MAE, RMSE, MAPE).
2. **RFM Customer Segmentation**: Uses **K-Means Clustering** across Recency (days since last purchase), Frequency (total orders), and Monetary (total spend) log-transformed vectors to segment customers into 4 tiers: *Champions, Loyal & Active, Potential Loyalists, and At Risk*.

---

### Q14: Why did you evaluate forecasting on a chronological hold-out set instead of random train/test split?
**Answer:** In time-series data, observations are auto-correlated across time. A random split causes **data leakage** because future information leaks into past predictions. A strict chronological split (first 80% of days for training, last 20% for testing) guarantees genuine generalization assessment.

---

### Q15: What is the processing throughput of your Big Data pipeline?
**Answer:** On a standard quad-core developer laptop, the PySpark pipeline processed the full **541,909 records in ~5 minutes**, achieving a throughput of **~1,810 records/second**.

---

### Q16: How did you benchmark scalability?
**Answer:** In `src/analytics/benchmark.py`, we designed a controlled scalability module that synthesizes scaled workloads (10,000, 25,000, 50,000, 100,000 records). Each synthetic record is clearly prefixed with `SYN-` to prevent polluting real data. The module measures stage latency (transform vs aggregation) and throughput curves.

---

### Q17: What are the 7 pages of the SalesPulse Analytics dashboard?
**Answer:**
1. **Sales Overview**: Executive KPI cards, monthly revenue/order trend, top 5 products, and checkout breakdown.
2. **Product Analytics**: Top products by revenue and volume, pricing distribution, and interactive catalog search.
3. **Sales Trends**: Monthly progression, Month-over-Month growth rates (%), daily fluctuations, and weekly/hourly seasonality.
4. **Customer and Regional**: Geographic revenue breakdown, UK vs International markets, and repeat customer retention.
5. **Data Management & Quality**: Pipeline execution controls, data quality health audit, and Amazon S3 sync management.
6. **Forecasting & Segmentation**: 30-day predictive demand forecasting and RFM K-Means clustering.
7. **System Performance**: Real pipeline latency breakdown by stage, throughput metrics, and synthetic scalability benchmarks.

---

### Q18: What automated test suite was created and what does it cover?
**Answer:** We wrote **29 unit and integration tests** using `pytest` covering:
- Schema conformance and missing columns
- Missing value analysis and data quality scoring
- CustomerID normalization and duplicate removal
- Cancellation flags and revenue calculations
- Spark SQL KPIs, top products, and MoM growth
- Local storage and S3 error handling using mocks
- Time-series forecasting hold-out accuracy and RFM clustering
- Dashboard formatting and data loaders
**All 29 tests pass with 100% success.**

---

### Q19: What is Catalyst Optimizer in Apache Spark?
**Answer:** Catalyst is Spark SQL's query optimization framework. It represents query plans as tree structures and applies rule-based and cost-based optimizations across four phases:
1. **Analysis**: Resolves column names and data types against the catalog.
2. **Logical Optimization**: Applies constant folding, predicate pushdown, and projection pruning.
3. **Physical Planning**: Selects efficient physical execution algorithms (e.g. BroadcastHashJoin vs SortMergeJoin).
4. **Code Generation**: Generates compact Java bytecode using whole-stage code generation.

---

### Q20: How would you deploy this application in a commercial cloud environment?
**Answer:**
1. **Storage**: Host raw ingestion drops and processed Parquet partitions on **Amazon S3**.
2. **Compute**: Orchestrate periodic batch runs on **AWS EMR** (running distributed PySpark on EC2 spot instances).
3. **Workflow Orchestration**: Schedule daily runs via **AWS Step Functions** or **Apache Airflow**.
4. **Serving Layer**: Containerize the Streamlit dashboard via Docker and deploy on **AWS ECS (Fargate)** or an **EC2 instance** behind an Application Load Balancer with HTTPS.
5. **Monitoring**: Route execution logs and alerts to **AWS CloudWatch**.
