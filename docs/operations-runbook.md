# Operations runbook

## 1. Refresh cadence
- Hourly refresh during weekday business hours

## 2. Typical failure modes
- Processing layer late (stale data risk)
- Reference file schema changes
- Parent mapping drift
- Credit agency extract gaps

## 3. Troubleshooting
- Start with dataset refresh status
- Run dataset-level validation checks
- Confirm parent mapping integrity
