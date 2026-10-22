# Cloud Computing (CC) AWS Guide & Zero-Cost Cloud Deployment

## 1. Cloud Architecture & Principles

SalesPulse Analytics demonstrates modern cloud-native principles:
- **Decoupled Compute and Storage**: The compute engine (Apache Spark) is completely stateless. It pulls raw data from Amazon S3 and writes results back to S3.
- **Enterprise Storage Organization**: S3 bucket objects follow structured logical prefixes:
  - `s3://<bucket>/raw/`
  - `s3://<bucket>/processed/`
  - `s3://<bucket>/analytics/`
  - `s3://<bucket>/reports/`
  - `s3://<bucket>/metadata/`
- **Security by Design**: 
  - S3 bucket is strictly **Private** (Block all public access enabled).
  - Server-Side Encryption (`AES256`) is enforced on all uploaded objects.
  - IAM Least-Privilege access policy ensures only necessary S3 permissions (`s3:PutObject`, `s3:GetObject`, `s3:ListBucket`) are granted.
  - No credentials or access keys are ever hardcoded or committed to version control.

---

## 2. Zero-Cost (₹0) Guarantee & AWS Free Tier Guardrails

| AWS Service | Free Tier Monthly Allowance | Project Usage Strategy | Out-of-Pocket Cost |
| :--- | :--- | :--- | :--- |
| **Amazon S3** | 5 GB Standard Storage, 20,000 GET, 2,000 PUT | Project dataset is ~46 MB raw + ~10 MB processed (total < 100 MB, well within 5 GB limit). | **₹0.00** |
| **AWS EC2** | 750 hours/month of `t2.micro` or `t3.micro` (Linux) | Host Streamlit app or run batch pipeline on a single free-tier eligible instance. | **₹0.00** |
| **AWS CloudWatch** | 10 custom metrics, 5 GB log ingestion | Monitor pipeline batch execution logs. | **₹0.00** |
| **AWS IAM** | Always Free | Least-privilege roles for EC2 and S3 access. | **₹0.00** |

> [!CAUTION]
> **AWS Cost Guardrail**: Never create multi-node Amazon EMR clusters or RDS database instances for initial academic review unless explicitly approved and budgeted, as EMR incurs separate per-instance charges beyond EC2!

---

## 3. Step-by-Step AWS Setup & Optional Deployment

### Step 1: Create a Private Amazon S3 Bucket
1. Log into the [AWS Management Console](https://console.aws.amazon.com/).
2. Navigate to **S3** ➔ **Create bucket**.
3. Choose a globally unique bucket name (e.g., `salespulse-analytics-<your-rollno>`).
4. Select Region: `us-east-1` (or your nearest region).
5. Ensure **"Block all public access"** is **CHECKED** (100% Private).
6. Enable **Server-side encryption** (SSE-S3 / AES-256).
7. Click **Create bucket**.

### Step 2: Create Least-Privilege IAM Policy
Create an IAM Policy named `SalesPulseS3Policy` with the following JSON:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "SalesPulseS3Access",
            "Effect": "Allow",
            "Action": [
                "s3:ListBucket",
                "s3:GetBucketLocation"
            ],
            "Resource": "arn:aws:s3:::salespulse-analytics-*"
        },
        {
            "Sid": "SalesPulseObjectOperations",
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:DeleteObject"
            ],
            "Resource": "arn:aws:s3:::salespulse-analytics-*/*"
        }
    ]
}
```

### Step 3: EC2 Single-Instance Deployment (Optional)
If presenting a live cloud deployment:
1. Launch an EC2 instance:
   - **AMI**: Ubuntu 22.04 LTS (HVM) or Amazon Linux 2023.
   - **Instance Type**: `t2.micro` or `t3.micro` (Free Tier eligible).
   - **IAM Role**: Attach an IAM role containing `SalesPulseS3Policy`.
   - **Security Group**: Inbound TCP Port 22 (SSH from your IP) and Port 8501 (Streamlit dashboard).
2. Connect to the EC2 instance via SSH:
   ```bash
   ssh -i your-key.pem ubuntu@ec2-xx-xx-xx-xx.compute-1.amazonaws.com
   ```
3. Install dependencies:
   ```bash
   sudo apt-get update
   sudo apt-get install -y openjdk-11-jre-headless python3-pip python3-venv git
   git clone https://github.com/<your-username>/ecommerce-sales-analytics.git
   cd ecommerce-sales-analytics
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
4. Run the Streamlit application in the background:
   ```bash
   nohup streamlit run app.py --server.port 8501 --server.address 0.0.0.0 > streamlit.log 2>&1 &
   ```
5. Open your browser and navigate to: `http://<EC2-Public-IP>:8501`.
