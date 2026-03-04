# Data quality and validation

## 1. Goals
- Detect regressions early
- Prevent stale or malformed outputs from reaching stakeholders
- Provide confidence in reported KPIs

## 2. Dataset checks
### Aging
- Bucket sum equals InvoiceAR
- NetAR equals invoice + credit bucket logic
- No negative exposure components
- Row count stability checks

### Payment Breakdown
- No negative applied amounts
- Bucket ordering stable
- Directional reconciliation vs AR payment totals

### Parent mapping
- Parents[CustomerNo] uniqueness
- ParentName standardization checks (trim, casing)
- Join success rate thresholds (tracker and agency mapping)

## 3. Monitoring approach
- Scheduled refresh checks
- Trend checks for row counts and join rates
- Alerting strategy (manual or automated)
