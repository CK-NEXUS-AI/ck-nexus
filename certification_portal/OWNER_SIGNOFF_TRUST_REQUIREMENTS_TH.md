# Owner Sign-off Trust Requirements (Thailand)

Status: engineering requirements only; not legal advice and not a production approval.

## Current implementation status

The Certification Portal currently creates an Ed25519 signature with an in-memory,
ephemeral demo key. The preview endpoint accepts a name and role supplied by the
requester. It does not authenticate the person's identity, establish authority to
act for an organization, prove exclusive control of a signing key, or provide a
trusted timestamp or certificate chain.

Therefore, OWNER_SIGNOFF_PREVIEW_ONLY is a cryptographic demonstration, not
proof that the named person signed, not an organizational approval, and not a
claim of legal validity.

## Thailand legal design inputs

The Electronic Transactions Act B.E. 2544 (2001), as amended, distinguishes
between the general electronic-signature requirements and the reliability
requirements for a reliable electronic signature.

ETDA's guidance on Section 9 says the method should be capable of identifying
the signatory and indicating that person's approval of the information, and
should be reliable for the purpose and circumstances.

Section 26 describes a reliable electronic signature with controls including:
- signature-creation data are linked to the signatory and no other person;
- the signatory controls those data at signing time;
- later changes to the signature are detectable; and
- changes to the signed information are detectable where integrity assurance is
  the purpose.

Section 27 also places duties on signatories to protect signature-creation data
and report compromise.

Official references:
- ETDA FAQ, e-Signature (Thai):
  https://www.etda.or.th/th/contact/faq/e-Signature.aspx
- Electronic Transactions Act (No. 4), B.E. 2562 (2019), ETDA English translation:
  https://www.etda.or.th/getattachment/0eb0d802-e692-4a56-ae4e-004da7f343c5/ETA-4-ACT-ENG-Version.aspx
- Electronic Transactions Act, ETDA English translation, Sections 25-27:
  https://www.etda.or.th/getattachment/8faa736b-3235-49c8-8b01-d37ff53a9a45/ENG-Version.aspx

The official Thai text in the Government Gazette prevails over translations.
Specific document classes may have additional legal or sector rules; obtain
qualified Thai legal review before treating this workflow as legally sufficient.

## Required controls before production sign-off

1. Identity proofing: verify the person through a documented, risk-appropriate
   identity process; retain the verification result and assurance level.
2. Authority: verify the person's role and authority to approve the exact system,
   organization, scope, and validity period.
3. Intent: show the exact immutable document/manifest digest and approval
   statement before consent; record explicit affirmative action.
4. Key control: use a signer-controlled or appropriately governed signing key;
   never use an ephemeral server demo key as an owner's legal-signature key.
5. Integrity: sign a canonical, versioned payload containing the subject digest,
   signer identity reference, authority reference, purpose, consent, and time.
6. Evidence: retain certificate chain or trust material, revocation/status
   evidence, trusted timestamp where required, audit trail, and verification
   instructions.
7. Lifecycle: support key rotation, revocation, compromise reporting, retention,
   access controls, and independent verification.
8. Legal review: determine whether the document type, parties, and intended use
   require additional formality, a particular certificate provider, or other
   sector-specific controls.

## Release gate

Until the controls above are implemented and independently verified:
- keep the endpoint labelled preview/demo only;
- do not issue or display a production certificate;
- do not represent a name field or cryptographic signature alone as identity
  proof, organizational authority, or legal acceptance;
- keep CK-NEXUS production status NO-GO.
