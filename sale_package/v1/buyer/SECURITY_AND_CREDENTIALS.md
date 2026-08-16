# Security and Credentials

## Delivery rule

The delivered source archive must contain no real API keys, OAuth access/refresh tokens, passwords, private keys, production databases or personal customer data.

## Buyer setup

The buyer creates/authorizes its own provider accounts and stores credentials outside source control. Use `.env.local` only for local evaluation and use a suitable secret store/credential broker for hosted environments.

## OAuth and external services

OAuth consent, MFA, CAPTCHA and platform-specific account verification remain controlled by the external service and account owner. CK-NEXUS must not bypass those controls.

## Token lifecycle

Legitimate refresh/rotation may maintain an already-authorized connection. Rotation must not be used to evade quotas, credits, rate limits or provider terms.

## Public deployment

For public internet exposure, deploy behind HTTPS and enforce authentication/access control, rate limiting, logging, secret management and the remaining production qualification gates appropriate to the buyer's risk profile.
