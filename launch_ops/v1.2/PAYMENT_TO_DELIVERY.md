# Payment to Delivery Workflow

## Before payment
1. agree product scope and transaction model;
2. send quotation/commercial schedule;
3. ensure buyer has seen Known Limitations and product classification;
4. do not send source ZIP as a pre-payment preview; use demo/screenshots/docs instead.

## Payment verification
Payment is verified only through the seller's approved payment provider/bank record. This repository stores no bank credentials and performs no charge or refund action.

Record:
- transaction_id
- buyer/legal entity
- agreed amount/currency
- invoice/quotation reference
- payment status
- payment verified timestamp
- verifier identity

## Delivery
Before sending:
- use the canonical buyer ZIP;
- calculate/compare SHA-256;
- ensure no seller-only kit is included;
- ensure no secrets/user data exist;
- complete delivery record.

Send:
- buyer delivery ZIP;
- SHA-256 sidecar;
- executed commercial schedule/license document as applicable;
- acceptance instructions.

Never send:
- Seller Sales Kit;
- internal pricing floor;
- `.env.local`;
- OAuth tokens/API keys/private keys;
- production databases/user content.

## Acceptance
Buyer verifies checksum, extracts ZIP, runs Demo Mode, reviews included docs and signs/records acceptance according to the executed commercial schedule.
