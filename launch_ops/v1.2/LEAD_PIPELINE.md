# Lead Pipeline

Use these stages:

`NEW -> QUALIFIED -> DEMO_SCHEDULED -> DEMO_DONE -> QUOTED -> NEGOTIATION -> WON_PENDING_PAYMENT -> PAID_PENDING_DELIVERY -> DELIVERED -> ACCEPTED -> SUPPORT -> CLOSED`

Loss states:
`UNQUALIFIED`, `LOST_PRICE`, `LOST_TIMING`, `LOST_SCOPE`, `NO_RESPONSE`.

Minimum fields:
- lead_id
- buyer_name
- contact
- stage
- source
- intended_use
- technical_fit: FIT / PARTIAL / NO_FIT
- product_scope: SOURCE_BETA
- quoted_amount_thb
- quote_valid_until
- transaction_model
- demo_date
- payment_status: NOT_REQUESTED / PENDING / VERIFIED / REFUNDED
- delivery_status: NOT_READY / READY / DELIVERED / ACCEPTED
- buyer_package_sha256
- next_action
- next_action_due
- notes_redacted

Rules:
- never mark PAID from a screenshot alone if the seller's approved payment channel has not confirmed it;
- never mark DELIVERED without recording the exact package hash;
- never promise Production Ready while release status is NO-GO;
- keep credentials and sensitive buyer data outside lead notes.
