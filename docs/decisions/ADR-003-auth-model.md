# ADR-003: Authentication model

## Status
Accepted

## Context
The user base for setlist-picker is friends coordinating at live events. The friction of signup / email confirmation / password reset is the wrong tradeoff for that context — people are standing at a venue trying to share a link with their crew. Multi-device sync, account recovery, profile management all add complexity that the v1 user doesn't need.

## Decision

**Anonymous, group-code based access.**

- A group has an 8-character base32 (Crockford alphabet) code, embedded in a shareable URL: `https://setlist-picker.example/g/AB7K9MNP`.
- Anyone who opens that URL can join the group by entering a display name. No email, no password, no signup.
- On join, a UUID `member_id` is assigned and stored in a long-lived cookie. That cookie is the credential — anyone with the cookie is recognized as that member.
- A separate browser / device joining the same group with the same display name gets a fresh `member_id`. Two devices logged in as "Jerome" are two distinct presences. Intentional — the v1 model treats devices as ephemeral.
- No admin / role / kick mechanic. Everyone in the group has equal privileges.

## Rationale

1. **Zero friction.** From URL to picking sets in under 30 seconds. No email confirmation flow, no password reset link, no profile picture picker.
2. **No PII to manage.** Display name + group code is the entire data footprint per user. No email addresses to leak, no passwords to hash + rotate, no GDPR data export endpoint.
3. **The URL is the credential.** Same model as a Google Docs share link or a Calendly meeting URL. Anyone with the link has access; that's the deal. Group codes are 8 characters base32 (~1.1 trillion entropy) — not enumerable by brute force.
4. **v2 layering is easy.** When (if) the product grows, "claim my group" via magic link can be added as an optional layer. Member IDs stay the same; an email gets linked to the member ID. Cross-device sync follows.

## Consequences

### Positive
- Lowest possible friction at the festival entry point.
- Tiny PII surface.
- No auth library to maintain.

### Negative
- No cross-device continuity in v1. If a user clears their browser data they re-join as a new member (with the same display name visible to friends, but treated as a separate presence in the data).
- No protection against a hostile actor finding a group code and joining. Mitigation: codes are non-enumerable; groups archive after 90 days of inactivity.
- No way to "kick" someone. Mitigation: cooperative group dynamics; users can always create a new group if needed.

## Forward compat

- "Claim my group" (v2): a logged-in member can attach an email to their member ID. Magic-link sign-in on subsequent device. Member ID continuity is preserved.
- Group-level role hierarchy (v2+): if user demand emerges, add an `is_creator` bool on `member` and gate certain endpoints (rename group, delete group) to creator-only.

## References
- [PRD.md](../PRD.md) § 5.1
- [ARCHITECTURE.md](../ARCHITECTURE.md) § Security / privacy
