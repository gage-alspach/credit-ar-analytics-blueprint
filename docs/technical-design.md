# Technical design

## 1. Overview
This document describes the technical implementation at the dataset level:
- Inputs (entities, not system-specific schemas)
- Grain
- High-level logic
- Business rules
- Output contract (fields and definitions)
- Validation checks
- Known limitations (technical debt)

## 2. Dataset specifications

### 2.1 Aging (Core AR)
**Purpose**
Customer-level AR aging, credits, payment summary, credit limits, and operational exposure.

**Grain**
One row per CustomerNo per company context.

**Inputs**
- ERP ledger detail (invoices, payments, credits, remaining open balances)
- ERP customer master (names, credit limits, payment terms)
- TMS shipments + exposure signals (open uncovered, in-transit, etc.)
- Invoice System not-invoiced signals (unbilled risk)

**High-level logic**
- Deduplicate ledger detail to a single authoritative record per open item.
- Build a point-in-time AR view up to an effective as-of date.
- Age open invoice balances using invoice date plus payment terms.
- Age open credits separately and net credits into aging buckets.
- Summarize payment history at the customer level.
- Join operational exposure and not-invoiced signals.
- Retain customers with zero AR but active exposure or credit limits.

**Key business rules**
- Positive open balances are treated as open invoices.
- Negative open balances represent credits (aged by credit posting date).
- Credits reduce net aging buckets (not allocated to specific invoices).
- Payment terms are derived from customer terms, with controlled overrides where needed.
- Exposure signals are directional and do not reconcile to AR totals by design.

**Output contract (selected fields)**
- CustomerNo, CustomerName
- CreditLimit
- InvoiceAR, OpenCredits, NetAR
- Aging buckets (Current, 1-30, 31-60, 61-90, 91+)
- Exposure components (open uncovered, in-transit, not invoiced)
- LastPaymentDate

**Validation**
- Sum of invoice aging buckets equals InvoiceAR.
- NetAR equals invoice buckets plus credit buckets.
- Exposure components are non-negative.
- Directional alignment checks against ERP AR balance.

**Known limitations**
- Payment term overrides should migrate to a reference table.
- Credit aging is not allocation-based and may differ from accounting allocation logic.
- Exposure aggregation may be unstable and should be treated as indicative.

---

### 2.2 Payment Breakdown (Applied Payments)

**Purpose**

Provide a structured view of payment behavior over time by analyzing when payments are applied relative to invoice due dates. This dataset enables trend analysis of payment timeliness and customer payment patterns.

**Grain**

One row per:

- CustomerNo  
- Company context  
- Apply month  
- Payment timeliness bucket  

**Inputs**

- ERP customer master  
  - Customer identifiers  
  - Customer names  
  - Payment terms

- ERP AR ledger detail  
  - Invoice records  
  - Payment records  
  - Application records linking payments to invoices

- Derived date logic  
  - As-of handling  
  - Month grouping logic

**High-level logic**

1. Identify invoice records and determine due dates using invoice posting date plus customer payment terms.
2. Identify all payment and credit application records linked to invoices.
3. For each payment application, determine how many days late the payment was at the time it was applied.
4. Assign each payment to a lateness bucket based on days past due at the time of application.
5. Group applied payment amounts by:
   - Customer
   - Month applied
   - Lateness bucket
6. Output a dataset optimized for time-series analysis and visualization.

**Key business rules**

- Only **applied payment amounts** are included.  
  Unapplied cash balances are excluded.

- Payment timeliness is evaluated based on **application date relative to invoice due date**, not payment receipt date.

- Payment terms used to derive due dates are taken from the customer master record, with controlled overrides where required.

- Payments applied **on or before the due date** are classified as **Current**.

- Payments applied **after the due date** are classified into lateness buckets based on the number of days late.

- All historical payment applications up to the effective as-of date are included.

**Output contract (selected fields)**

- CompanyID  
- CustomerNo  
- CustomerName  
- ApplyMonth  
- AsOfDate  
- LateBucket  
- BucketOrder  
- AmountApplied  

**Validation**

- Monthly applied totals should align directionally with payment activity reflected in AR balances.
- No negative applied payment amounts should appear.
- Lateness bucket ordering must remain stable for reporting and sorting purposes.

**Known limitations**

- Payment behavior reflects **application timing**, not the original receipt date of funds.
- Historical as-of logic exists but is primarily intended to ensure dataset consistency rather than support backdated reporting.

---

### 2.3 Parents (Unified Parent Mapping)

**Purpose**

Produce the authoritative customer-to-parent mapping used across the analytics model.  
This dataset combines manually maintained parent mappings with system-derived parent relationships to ensure full coverage.

**Grain**

One row per **CustomerNo**, mapped to a **ParentName**.

**Inputs**

- Parent mapping workbook (manual mapping)
- Customer system parent relationships (derived mapping)

**High-level logic**

1. Load the manually maintained parent mapping file.
2. Load system-derived parent relationships extracted from customer account records.
3. Standardize key formats (text normalization, trimming, consistent casing).
4. Identify customers that exist in system-derived mapping but are missing from the manual mapping.
5. Append system-derived rows to fill gaps in the manual mapping.
6. Remove rows with missing identifiers.
7. Output a unified mapping table.

**Key business rules**

- Manual mappings are treated as **authoritative** when present.
- System-derived mappings are used **only to fill gaps**, not to overwrite manual mappings.
- Customer identifiers must match the identifier used in operational systems.
- Parent names are standardized for consistent reporting and aggregation.

**Output contract (selected fields)**

- CustomerNo  
- CustomerName  
- ParentName  

**Validation**

- CustomerNo uniqueness should equal row count unless duplicates are intentionally documented.
- For customers present in the manual mapping file, the parent assignment must match the manual mapping.
- Sudden increases in unmapped customers should be investigated.

**Known limitations**

- Duplicate rows may occur if manual mapping files contain duplicate entries.
- Parent name consistency across reference files is required to ensure correct joins.

---

### 2.4 Credit Agency History

**Purpose**

Provide a standardized history of credit agency reports used to evaluate creditworthiness at the parent company level.

This dataset merges multiple credit agency sources into a single normalized structure optimized for reporting and time-series analysis.

**Grain**

One row per:

- ParentName  
- Reporting date  
- Credit agency source  
- Credit metric attribute

**Inputs**

- Credit agency history extract (Agency 1)
- Credit agency history extract (Agency 2)
- Customer master tracker (used for parent normalization)

**High-level logic**

1. Load historical credit agency extracts.
2. Normalize schema differences between agencies.
3. Align parent naming conventions using the customer master tracker.
4. Convert source data into a standardized attribute/value structure.
5. Output a unified dataset capable of supporting matrix-style reporting.

**Key business rules**

- Credit agency records must map to a standardized parent entity.
- Parent-level mapping is used rather than customer-level mapping.
- Attributes are stored in a normalized attribute/value format to support flexible reporting.
- Visualization-specific formatting rules are applied in the reporting layer rather than the dataset.

**Output contract (selected fields)**

- ParentName  
- ReportDate  
- SourceAgency  
- Attribute  
- Value  

**Validation**

- Each agency should have recent report dates within the expected update window.
- Parent mapping success rate should remain stable over time.
- Row counts should trend consistently with historical reporting volumes.

**Known limitations**

- Parent mapping depends on naming consistency in reference files.
- Schema changes in agency extracts require transformation updates.

---

### 2.5 Invoices Detail (Invoice-Level Aging)

**Purpose**

Provide invoice-level aging detail used by paginated reports and advanced investigation of customer balances.

This dataset exposes individual open items, their aging status, and associated document identifiers.

**Grain**

One row per **open ledger entry** representing either:

- An open invoice balance
- An unapplied payment or credit

**Inputs**

- ERP customer master  
  - Customer identifiers  
  - Payment terms

- ERP AR ledger detail  
  - Remaining balances  
  - Posting dates  
  - Document identifiers

**High-level logic**

1. Load customer master data and derive payment term days.
2. Extract ledger entries representing invoices and payments.
3. Deduplicate entries to ensure a single authoritative row per open item.
4. Construct point-in-time ledger records using an effective as-of date.
5. Calculate due dates using posting date plus payment terms.
6. Assign aging buckets based on days past due.
7. Output invoice-level rows including bucket assignments and document identifiers.

**Key business rules**

- All rows with non-zero remaining balances are included.
- Positive balances represent **open invoices**.
- Negative balances represent **unapplied payments or credits**.

Due date logic differs by entry type:

- Invoice entries  
  Due date = invoice posting date + payment terms

- Payment or credit entries  
  Due date = posting date (treated as immediately due for aging display)

Document number selection follows this priority:

1. Invoice document identifier (if available)
2. Payment or credit document identifier
3. Fallback identifier from the most recent associated transaction

**Output contract (selected fields)**

- CustomerNo  
- CustomerName  
- PostingDate  
- DueDate  
- DaysPastDue  
- OpenAmount  
- Aging buckets (Current, 1-30, 31-60, 61-90, 91+)  
- DocumentType  
- DocumentNumber  
- LedgerEntryID  
- TermsDays  
- EffectiveAsOfDate  

**Validation**

- Aging bucket totals must equal the open amount for each row.
- Customer identifiers must not be null.
- Document coverage should remain high; spikes in missing identifiers indicate upstream data issues.

**Known limitations**

- Aging logic for negative balances is designed for reporting consistency rather than accounting allocation.
- As-of logic exists for point-in-time analysis but is typically used for latest-state reporting.
