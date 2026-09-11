# BeAstar.io — Global Compliance Checklist

This is the non-negotiable list for a face-upload, AI-video, viral-sharing
app operating worldwide. None of these are optional at scale — TikTok,
Instagram, and YouTube will enforce several of them on your behalf whether
you build for them or not (by removing content or the app), so building
them in yourself is cheaper than getting delisted later.

## 1. Age & consent
- Minimum signup age: 13 (enforced in `schema.sql` via CHECK constraint).
- Ages 13–17: require verifiable parental consent before face upload is
  enabled (COPPA in the US; similar rules under UK/EU age-appropriate
  design codes). Simple "check the box" is not sufficient for COPPA once
  you're collecting biometric-adjacent data (a face embedding).
- 18+: standard consent flow, but still disclose face-data handling
  explicitly at signup, not buried in a general ToS.

## 2. Biometric / face data handling
- Store a face **embedding** (a derived vector/hash), never the raw selfie,
  as the long-term reference for self-match checks.
- Several US states (Illinois BIPA, Texas, Washington) have specific
  biometric-data statutes with statutory damages — get consent language
  right before storing anything face-derived, and give users a way to
  delete their embedding.
- EU/UK: biometric data for identification is "special category" data
  under GDPR — needs explicit consent and a documented lawful basis.

## 3. AI-generated content disclosure
- Every rendered video needs a visible, non-removable indicator that it's
  AI-generated. This is required by:
  - TikTok, Meta (Instagram/Facebook), and YouTube's own synthetic-media
    policies (they'll auto-label or remove undisclosed AI content anyway).
  - The EU AI Act's transparency obligations for synthetic media.
  - A growing list of US state laws on AI-generated content disclosure.
- Implementation note already in `app/main.py`: burn the label into the
  render itself, not an overlay a user can crop out.

## 4. Right of publicity / IP
- No real celebrity names, franchise names, or trademarked show/venue
  branding in scenario templates — confirmed decision, reflected in
  `scenarios` table design (generic names only).
- If you ever allow a second real person's face in a video (friend/family
  co-star), that person needs their own consent flow — one user clicking
  "yes" for someone else isn't sufficient.

## 5. Known-public-figure blocking
- The face-verification pipeline (`verify-face` stub in `main.py`) must
  reject uploads that match a known public figure, independent of the
  age/consent checks above — this is what prevents the app being used to
  impersonate someone other than the account holder.

## 6. Data protection general
- GDPR (EU/UK users): right to access, right to deletion, data processing
  agreement with any AI video-gen vendor you use (they're a sub-processor).
- CCPA/CPRA (California users): right to know, right to delete, right to
  opt out of sale/sharing of personal data.
- Have a real deletion path: deleting a user should delete their face
  embedding, stored videos, and generation history, not just deactivate
  the account row.

## 7. Payments
- Stripe (or equivalent) handles most PCI-DSS burden for you — never
  store raw card numbers yourself.
- Local payment methods (GCash, PayTM, etc.) each bring their own
  regional compliance; add per-market as you expand rather than trying to
  integrate all of them for a Philippines-first launch.

## 8. Content moderation
- Automated moderation pass on generated output before it's shareable —
  needed both for platform ToS compliance and to catch attempted misuse
  of the generation pipeline itself.
- A user reporting/flagging mechanism, with a real response SLA — required
  under the EU Digital Services Act once you have EU users at meaningful
  scale, and good practice regardless.

## 9. Aspiration/net-worth content (the "how'd you get rich" feature)
- Self-reported net worth is stored as a broad band (`under_100k`,
  `100k_1m`, `1m_5m`, `5m_plus`), never an exact figure, and every API
  response includes a `display_note` marking it self-reported/unverified —
  the app must never render it as a verified claim.
- This content category — "here's my dream + proof I made it" — is the
  exact template get-rich-quick and fake-guru scams use, independent of
  whether any individual poster is genuine. Posts default to
  `moderation_status = 'pending'` and are excluded from the public feed
  until approved; anything mentioning specific financial products,
  "guaranteed returns," investment signals, or external payment links
  should route to manual review, not just automated moderation.
- Several jurisdictions (UK FCA financial promotion rules, various US
  state laws) specifically regulate financial-advice-adjacent content —
  worth a compliance review before this feature goes live broadly, not
  just before payments do.

## Priority order for a Philippines-first soft launch
1. Age gate + basic consent (already in schema)
2. AI-disclosure label burned into renders
3. Known-public-figure block in face verification
4. Face-embedding-only storage (never raw selfies long-term)
5. Basic content moderation pass
6. Full GDPR/CCPA tooling — before EU/US user growth, not day one
