## Spectre risk report

**Overall severity:** `red`

### Findings

| Clause | Status | Severity | Confidence | Summary |
|--------|--------|----------|------------|---------|
| demo_vendor_agreement_5f6caa32d682_c000 | at_risk | medium | 0.75 | Data processing clause should explicitly reference consent and purpose limitatio |
| demo_vendor_agreement_5f6caa32d682_c001 | at_risk | high | 0.74 | Data processing clause — verify consent, purpose limitation, and DPA flow-down. |
| demo_vendor_agreement_5f6caa32d682_c002 | violation | violation | 0.92 | Corpus match: Sub-processor flow-down (GDPR Recital 81) |
| demo_vendor_agreement_5f6caa32d682_c003 | violation | violation | 0.92 | Corpus match: General principle for transfers (GDPR Art.44) |
| demo_vendor_agreement_5f6caa32d682_c004 | violation | violation | 0.92 | Corpus match: General principle for transfers (GDPR Art.44) |
| demo_vendor_agreement_5f6caa32d682_c005 | violation | violation | 0.92 | Corpus match: General principle for transfers (GDPR Art.44) |

## Proposed redlines

### Clause `demo_vendor_agreement_5f6caa32d682_c000`

**Regulation:** DPDP §6

*Data processing clause should explicitly reference consent and purpose limitation.*

```diff
- Section 1. Definitions. Personal Data means information relating to an identified person.
+ The Vendor shall process Personal Data only on Customer's documented instructions and, where required under the Digital Personal Data Protection Act 2023, only with valid, specific, informed, and unambiguous consent of the data principal.
```

### Clause `demo_vendor_agreement_5f6caa32d682_c001`

**Regulation:** DPDP §6, GDPR Art.28

*Data processing clause — verify consent, purpose limitation, and DPA flow-down.*

```diff
- Section 8. Data Processing. The Vendor may process Personal Data to provide the Service.
+ The Vendor shall process Personal Data only on Customer's documented instructions and, where required under the Digital Personal Data Protection Act 2023, only with valid, specific, informed, and unambiguous consent of the data principal.
```

### Clause `demo_vendor_agreement_5f6caa32d682_c002`

**Regulation:** GDPR Recital 81

*Corpus match: Sub-processor flow-down (GDPR Recital 81)*

```diff
- Section 14.3 Sub-processors. The Vendor may engage unlimited sub-processors worldwide without notice to Customer and without flow-down of data protection obligations.
+ The Vendor shall not engage any sub-processor without (i) thirty (30) days' prior written notice, (ii) Customer's right to object on reasonable grounds, and (iii) a written agreement imposing data protection obligations equivalent to this Agreement. Approved sub-processors are listed in Annex B.
```

### Clause `demo_vendor_agreement_5f6caa32d682_c003`

**Regulation:** GDPR Art.44

*Corpus match: General principle for transfers (GDPR Art.44)*

```diff
- Section 15. Liability. Vendor's total liability shall be unlimited. Customer indemnifies Vendor for all claims including regulatory penalties.
+ Section 15. Liability. Vendor's total liability shall be unlimited. Customer indemnifies Vendor for all claims including regulatory penalties.  [Amended per Spectre recommendation: GDPR Art.44]
```

### Clause `demo_vendor_agreement_5f6caa32d682_c004`

**Regulation:** GDPR Art.44

*Corpus match: General principle for transfers (GDPR Art.44)*

```diff
- Section 20. Termination. Either party may terminate with 7 days notice. Upon termination Vendor may retain all Customer data indefinitely for analytics and product improvement.
+ The Vendor shall process Personal Data only on Customer's documented instructions and, where required under the Digital Personal Data Protection Act 2023, only with valid, specific, informed, and unambiguous consent of the data principal.
```

### Clause `demo_vendor_agreement_5f6caa32d682_c005`

**Regulation:** GDPR Art.44

*Corpus match: General principle for transfers (GDPR Art.44)*

```diff
- Section 22. Cross-border. Customer data may be transferred to any country where Vendor maintains facilities including the United States without additional safeguards.
+ The Vendor shall process Personal Data only on Customer's documented instructions and, where required under the Digital Personal Data Protection Act 2023, only with valid, specific, informed, and unambiguous consent of the data principal.
```
