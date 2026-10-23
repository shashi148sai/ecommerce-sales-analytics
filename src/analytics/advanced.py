"""
SalesPulse Analytics - Advanced Analytics Module
Implements time-series sales forecasting (with hold-out historical evaluation)
and RFM (Recency, Frequency, Monetary) customer segmentation with K-Means clustering.
"""

from typing import Dict, Any, Tuple, Optional, List
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error


def validate_and_prepare_daily_series(
    daily_sales_df: pd.DataFrame,
    min_observed_days: int = 14
) -> pd.DataFrame:
    """
    Validates, normalizes, and prepares a daily time-series DataFrame into a canonical schema:
    ['Date', 'DailyRevenue']
    
    Robust against:
    - Differing date column names ('Date', 'InvoiceDate', 'order_date', 'transaction_date', etc.)
    - Differing revenue column names ('DailyRevenue', 'Revenue', 'TotalRevenue', 'LineTotal', 'SalesAmount', etc.)
    - Missing or unparseable timestamps (coerced and filtered safely)
    - Null or negative revenue amounts (cleaned and clamped)
    - Multiple transactions on the same day (aggregated by date)
    - Insufficient observed history (checked BEFORE calendar resampling to prevent fabricated zeroes)
    - Extremely sparse dates (checked to avoid creating artificial data across multi-year gaps)
    """
    if daily_sales_df is None or len(daily_sales_df) == 0:
        raise ValueError("Cannot perform forecasting: input dataset is empty.")
        
    df = daily_sales_df.copy()
    
    # Identify Date column
    date_col = None
    for candidate in ["Date", "InvoiceDateOnly", "InvoiceDate", "order_date", "date", "OrderDate", "transaction_date"]:
        if candidate in df.columns:
            date_col = candidate
            break
    if date_col is None:
        for c in df.columns:
            c_str = str(c).strip().lower()
            if "date" in c_str or "time" in c_str or "day" in c_str:
                date_col = c
                break
    if date_col is None:
        raise ValueError("Cannot perform forecasting: no usable transaction date column found in dataset.")
        
    # Identify Revenue column
    rev_col = None
    for candidate in ["DailyRevenue", "Revenue", "TotalRevenue", "LineTotal", "SalesAmount", "Sales", "NetRevenue", "Amount"]:
        if candidate in df.columns:
            rev_col = candidate
            break
    if rev_col is None:
        for c in df.columns:
            if c != date_col:
                c_str = str(c).strip().lower()
                if any(term in c_str for term in ["rev", "sales", "amount", "total", "price"]):
                    rev_col = c
                    break
    if rev_col is None:
        raise ValueError("Cannot perform forecasting: no usable revenue column (e.g. 'DailyRevenue', 'LineTotal') found.")
        
    # Standardize column parsing and clean invalid data
    clean_dates = pd.to_datetime(df[date_col], errors="coerce")
    clean_rev = pd.to_numeric(df[rev_col], errors="coerce")
    
    clean_df = pd.DataFrame({"Date": clean_dates, "DailyRevenue": clean_rev})
    clean_df = clean_df.dropna(subset=["Date", "DailyRevenue"])
    
    if len(clean_df) == 0:
        raise ValueError("Cannot perform forecasting: no valid dates or revenue values found in dataset.")
        
    # Non-negative revenue clamping (returns handled by isolating gross/net sales beforehand)
    clean_df["DailyRevenue"] = clean_df["DailyRevenue"].clip(lower=0.0)
    
    # Normalize timestamps to date only and aggregate multi-transaction days
    clean_df["Date"] = clean_df["Date"].dt.normalize()
    daily_grouped = clean_df.groupby("Date", as_index=False)["DailyRevenue"].sum()
    daily_grouped = daily_grouped.sort_values("Date").reset_index(drop=True)
    
    observed_days = len(daily_grouped)
    if observed_days < min_observed_days:
        raise ValueError(
            f"Insufficient time-series history for forecasting: minimum {min_observed_days} distinct observed daily data points required, but found {observed_days}."
        )
        
    positive_days = (daily_grouped["DailyRevenue"] > 0).sum()
    if positive_days < max(min_observed_days // 2, 7):
        raise ValueError(
            f"Insufficient positive daily revenue records ({positive_days} days) to train a predictive model."
        )
        
    # Check date span density to prevent fabricating hundreds of zeroes across sparse multi-year gaps
    min_date = daily_grouped["Date"].min()
    max_date = daily_grouped["Date"].max()
    span_days = (max_date - min_date).days + 1
    if span_days > 0 and (observed_days / span_days) < 0.10:
        raise ValueError(
            f"Historical transaction dates are too sparse for continuous time-series forecasting: observed {observed_days} active days across a {span_days}-day calendar span ({observed_days/span_days:.1%} density)."
        )
        
    # Continuous calendar regularization for regular business operations (closed days set to 0.0)
    resampled = daily_grouped.set_index("Date").resample("D")["DailyRevenue"].sum().fillna(0.0).reset_index()
    return resampled


def perform_sales_forecasting(
    daily_sales_df: pd.DataFrame,
    forecast_days: int = 30,
    test_ratio: float = 0.2
) -> Dict[str, Any]:
    """
    Executes time-series sales forecasting using lagged temporal regression
    with day-of-week seasonality, evaluated rigorously on a chronological hold-out set.
    
    Args:
        daily_sales_df: DataFrame containing date and daily revenue columns.
        forecast_days: Number of future days to project.
        test_ratio: Proportion of recent historical data reserved for hold-out evaluation.
        
    Returns:
        Dictionary containing historical actuals, train/test evaluation metrics (MAE, RMSE, MAPE),
        and future forecasted values with consistent schema containing Date, DailyRevenue,
        ActualRevenue, and PredictedRevenue.
    """
    df = validate_and_prepare_daily_series(daily_sales_df, min_observed_days=14)
    n_total = len(df)
        
    # Feature engineering: trend index, day of week, day of month, lags
    df["time_idx"] = np.arange(n_total)
    
    # Compatible day-of-week extraction for modern pandas versions
    if hasattr(df["Date"].dt, "day_of_week"):
        df["day_of_week"] = df["Date"].dt.day_of_week
    else:
        df["day_of_week"] = df["Date"].dt.dayofweek
        
    df["day_of_month"] = df["Date"].dt.day
    df["lag_1"] = df["DailyRevenue"].shift(1).bfill()
    df["lag_7"] = df["DailyRevenue"].shift(7).bfill()
    df["rolling_mean_7"] = df["DailyRevenue"].shift(1).rolling(7, min_periods=1).mean().bfill()
    
    # Chronological train/test split (NEVER random split for time series)
    n_test = max(int(n_total * test_ratio), 5)
    n_train = n_total - n_test
    
    feature_cols = ["time_idx", "day_of_week", "day_of_month", "lag_1", "lag_7", "rolling_mean_7"]
    
    train_df = df.iloc[:n_train].copy()
    test_df = df.iloc[n_train:].copy()
    
    X_train = train_df[feature_cols]
    y_train = train_df["DailyRevenue"]
    
    X_test = test_df[feature_cols]
    y_test = test_df["DailyRevenue"]
    
    # Fit Ridge regularized regression
    model = Ridge(alpha=1.0)
    model.fit(X_train, y_train)
    
    # Predictions on hold-out test set
    test_preds = np.maximum(0, model.predict(X_test))
    
    # Metrics
    mae = mean_absolute_error(y_test, test_preds)
    rmse = np.sqrt(mean_squared_error(y_test, test_preds))
    # Safe MAPE calculation (avoiding divide-by-zero on quiet days)
    non_zero_mask = y_test > 0
    if non_zero_mask.sum() > 0:
        mape = np.mean(np.abs((y_test[non_zero_mask] - test_preds[non_zero_mask]) / y_test[non_zero_mask])) * 100
    else:
        mape = 0.0
        
    test_df["PredictedRevenue"] = np.round(test_preds, 2)
    
    # Generate future projections sequentially
    last_date = df["Date"].iloc[-1]
    last_idx = df["time_idx"].iloc[-1]
    
    future_dates = [last_date + pd.Timedelta(days=i) for i in range(1, forecast_days + 1)]
    future_records = []
    
    # Rolling sequence for future lags
    current_series = list(df["DailyRevenue"].values)
    
    for i, f_date in enumerate(future_dates, start=1):
        idx = last_idx + i
        dow = f_date.day_of_week if hasattr(f_date, "day_of_week") else f_date.dayofweek
        dom = f_date.day
        lag1 = current_series[-1]
        lag7 = current_series[-7] if len(current_series) >= 7 else current_series[-1]
        roll7 = np.mean(current_series[-7:]) if len(current_series) >= 7 else np.mean(current_series)
        
        feats_df = pd.DataFrame([[idx, dow, dom, lag1, lag7, roll7]], columns=feature_cols)
        pred = max(0.0, float(model.predict(feats_df)[0]))
        current_series.append(pred)
        
        pred_rounded = round(pred, 2)
        future_records.append({
            "Date": f_date.strftime("%Y-%m-%d"),
            "ForecastedRevenue": pred_rounded,
            "PredictedRevenue": pred_rounded,
            "DailyRevenue": pred_rounded,
            "LowerBound": round(max(0.0, pred - 1.96 * mae), 2),
            "UpperBound": round(pred + 1.96 * mae, 2)
        })
        
    forecast_df = pd.DataFrame(future_records)
    
    # Format actual history for plotting - provides BOTH DailyRevenue and ActualRevenue
    history_records = [
        {
            "Date": r["Date"].strftime("%Y-%m-%d"),
            "DailyRevenue": round(float(r["DailyRevenue"]), 2),
            "ActualRevenue": round(float(r["DailyRevenue"]), 2)
        }
        for _, r in df.iterrows()
    ]
    
    # Format test evaluation records - provides BOTH DailyRevenue and ActualRevenue along with PredictedRevenue
    test_eval_records = [
        {
            "Date": r["Date"].strftime("%Y-%m-%d"),
            "DailyRevenue": round(float(r["DailyRevenue"]), 2),
            "ActualRevenue": round(float(r["DailyRevenue"]), 2),
            "PredictedRevenue": round(float(r["PredictedRevenue"]), 2)
        }
        for _, r in test_df.iterrows()
    ]
    
    return {
        "evaluation_metrics": {
            "MAE": round(float(mae), 2),
            "RMSE": round(float(rmse), 2),
            "MAPE_percent": round(float(mape), 2),
            "train_days": int(n_train),
            "holdout_test_days": int(n_test)
        },
        "history": history_records,
        "holdout_evaluation": test_eval_records,
        "forecast": future_records
    }


def compute_rfm_segmentation(
    sales_df: pd.DataFrame,
    n_clusters: int = 4,
    reference_date: Optional[pd.Timestamp] = None
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Computes RFM (Recency, Frequency, Monetary) customer segmentation using K-Means clustering.
    
    Args:
        sales_df: Cleaned commercial transactions DataFrame with CustomerID, InvoiceDate, LineTotal, InvoiceNo.
        n_clusters: Number of behavioral segments to form (default: 4).
        reference_date: Cutoff date for recency calculation (defaults to max date + 1 day).
        
    Returns:
        Tuple of (customer_rfm_df, segment_summary_df):
        - customer_rfm_df: Customer level table with Recency, Frequency, Monetary, Cluster, and SegmentName.
        - segment_summary_df: Aggregated commercial attributes per customer tier.
    """
    df = sales_df.dropna(subset=["CustomerID"]).copy()
    if df.empty:
        empty_rfm = pd.DataFrame(columns=["CustomerID", "Recency", "Frequency", "Monetary", "Segment"])
        return empty_rfm, pd.DataFrame()
        
    df["InvoiceTimestamp"] = pd.to_datetime(df["InvoiceTimestamp"])
    
    if reference_date is None:
        reference_date = df["InvoiceTimestamp"].max() + pd.Timedelta(days=1)
        
    # Group by customer
    rfm = df.groupby("CustomerID").agg(
        Recency=("InvoiceTimestamp", lambda x: (reference_date - x.max()).days),
        Frequency=("InvoiceNo", "nunique"),
        Monetary=("LineTotal", "sum")
    ).reset_index()
    
    # Filter positive monetary
    rfm = rfm[rfm["Monetary"] > 0].copy()
    rfm["Monetary"] = np.round(rfm["Monetary"], 2)
    
    if len(rfm) < n_clusters:
        rfm["Cluster"] = 0
        rfm["Segment"] = "Valued Customer"
        summary = rfm.groupby("Segment").agg(
            CustomerCount=("CustomerID", "count"),
            AvgRecency=("Recency", "mean"),
            AvgFrequency=("Frequency", "mean"),
            AvgMonetary=("Monetary", "mean"),
            TotalRevenue=("Monetary", "sum")
        ).reset_index()
        return rfm, summary
        
    # Standardize RFM features (log-transform heavily skewed monetary & frequency)
    rfm_log = pd.DataFrame({
        "Recency": np.log1p(rfm["Recency"]),
        "Frequency": np.log1p(rfm["Frequency"]),
        "Monetary": np.log1p(rfm["Monetary"])
    })
    
    scaler = StandardScaler()
    rfm_scaled = scaler.fit_transform(rfm_log)
    
    # K-Means clustering
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    rfm["Cluster"] = kmeans.fit_predict(rfm_scaled)
    
    # Rank clusters by commercial value (Monetary & Frequency) to assign interpretable labels
    cluster_ranks = (
        rfm.groupby("Cluster")[["Monetary", "Frequency", "Recency"]]
        .mean()
        .sort_values(by=["Monetary", "Frequency"], ascending=[False, False])
        .index.tolist()
    )
    
    segment_names = [
        "Champions (High Value, High Loyalty)",
        "Loyal & Active (Consistent Buyers)",
        "Potential Loyalists (Recent, Moderate Spend)",
        "At Risk / Hibernating (Needs Re-engagement)"
    ]
    
    cluster_to_name = {
        cluster_id: segment_names[i] if i < len(segment_names) else f"Segment {i+1}"
        for i, cluster_id in enumerate(cluster_ranks)
    }
    
    rfm["Segment"] = rfm["Cluster"].map(cluster_to_name)
    
    # Summary per segment
    summary = rfm.groupby("Segment").agg(
        CustomerCount=("CustomerID", "count"),
        AvgRecency=("Recency", lambda x: round(x.mean(), 1)),
        AvgFrequency=("Frequency", lambda x: round(x.mean(), 1)),
        AvgMonetary=("Monetary", lambda x: round(x.mean(), 2)),
        TotalRevenue=("Monetary", lambda x: round(x.sum(), 2))
    ).reset_index().sort_values(by="TotalRevenue", ascending=False)
    
    return rfm, summary
