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
[Repeat the same structure: purpose, grain, inputs, logic, rules, output, validation, limitations]

---

### 2.3 Parents (Unified Parent Mapping)
[Repeat structure, emphasize manual mapping is authoritative and system mapping fills gaps]

---

### 2.4 Credit Agency History
[Repeat structure, emphasize ParentName mapping and bridge dependency]

---

### 2.5 Invoices Detail (Paginated Support)
[Repeat structure, emphasize invoice-level grain and bucket assignment]
