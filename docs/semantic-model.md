# Semantic model

## 1. Purpose
The Power BI dataset provides a governed semantic layer to support reporting without requiring reverse engineering of report files.

## 2. Table roles
- Dimensions: Parents, Unique Parents, DimMetric, Bucket, Customer Master Tracker (bridge)
- Facts: Aging, Payment Breakdown, Invoices Detail, Credit Agency History, Latest snapshots (optional)

## 3. Relationship contract
### 3.1 Customer anchor (CustomerNo)
Parents[CustomerNo] filters:
- Aging
- Invoices Detail
- Payment Breakdown
- Customer Master Tracker

Requirements:
- Parents[CustomerNo] must be unique.
- All facts must normalize CustomerNo formatting.

### 3.2 Parent anchor (ParentName)
Unique Parents[ParentName] filters:
- Credit Agency History and related risk/snapshot tables
- Customer Master Tracker (bridge)

Note:
One bi-directional relationship may exist for bridging and should be treated as a controlled exception.

## 4. Navigation behavior
- Customer analysis: Parents -> Aging / Invoices Detail / Payment Breakdown
- Parent analysis: Unique Parents -> Credit Agency History
- Bridge behavior: Customer Master Tracker supports parent naming normalization across sources

## 5. Measures (high impact)
- Total Past Due
- Total Exposure
- Credit Remaining
- Latest credit agency values (per parent)
