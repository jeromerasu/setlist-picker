# BE-010 — Member roster helper + COALESCE display-name resolution

**Wave:** 1
**Type:** BE
**Blocked by:** BE-003, BE-006
**Blocks:** BE-009, FE-005
**ADR references:** [ADR-006 § 2.3, § 4.12](../../decisions/ADR-006-initial-data-schema.md)

## 1. Problem statement

`MemberOut.display_name` is a COALESCE chain: `override → user.display_name → user.username`. Several endpoints (BE-009 group state, BE-017 snapshot, BE-007 join, BE-008 my-groups) all return Member identity. We need one canonical resolver to avoid drift.

## 2. Actual solution

Single helper `app/services/member_service.resolve_member_out(member: Member, user: User) -> MemberOut`. Returns the wire shape. All callers use this helper. There is no standalone `GET /api/groups/{code}/members` endpoint in v1 — the data already rides on `GET /api/groups/{invite_code}` (BE-009). This ticket exists to lock the COALESCE rule in a single place and add the test coverage for it independently of the surrounding endpoints.

Avatar color comes from `user.avatar_color` only (ADR-006 § 4.12 — no per-Member color in v1).

## 3. Files to touch

| Path | Edit purpose |
|---|---|
| `services/api/app/services/member_service.py` | New file — `resolve_member_out` + `resolve_member_out_batch`. |
| `services/api/app/services/group_service.py` | Use `resolve_member_out_batch` in BE-009's member fetch. |
| `services/api/tests/test_member_resolver.py` | See § 7. |
| `docs/CODEBASE_GUIDE.md` | Add a one-liner under "Services". |

## 4. Method signatures / new APIs

```python
# app/services/member_service.py
def resolve_member_out(member: Member, user: User) -> MemberOut: ...

def resolve_member_out_batch(rows: Iterable[tuple[Member, User]]) -> list[MemberOut]: ...
```

Algorithm:

```python
display_name = (
    member.display_name_override
    or user.display_name
    or user.username
    or "Member"  # final fallback — only reachable if all three are NULL, which a User invariant prevents
)
```

The `"Member"` fallback should be unreachable in correct app state. Log `member.display_name_all_null` at WARNING if hit.

## 5. Constants and thresholds

| Constant | Value | Rationale |
|---|---|---|
| COALESCE chain order | override → user.display_name → user.username | ADR-006 § 2.3, § 3.1 Q1. |
| Avatar color source | `user.avatar_color` | ADR-006 § 4.12. |
| Final fallback string | `"Member"` | Defensive; should never be reached. |

## 6. Edge cases enumerated

| Case | Expected behavior |
|---|---|
| `override="DJ"`, `user.display_name="Jerome"`, `user.username="jerome"` | "DJ". |
| `override=None`, `user.display_name="Jerome"`, `user.username="jerome"` | "Jerome". |
| `override=None`, `user.display_name=None`, `user.username="jerome"` | "jerome". |
| All three NULL (SSO user, never set display_name) | "Member" + WARN log. |
| `override=""` (empty string) | Empty string is falsy in Python's `or` — falls through to user.display_name. But our service layer rejects empty overrides at write time (Pydantic min_length=1), so this case is unreachable in normal flow. Test asserts the fallthrough anyway. |
| Overrides containing only emoji `"🎵"` | Returned verbatim. |
| Overrides with leading/trailing whitespace | Stored stripped at write time; resolver doesn't strip. |

## 7. Acceptable validation

**Tests that MUST exist:**

| Test name | Assertion |
|---|---|
| `test_resolve_uses_override_when_present` | All three set → returns override. |
| `test_resolve_falls_back_to_user_display_name` | override=None → returns user.display_name. |
| `test_resolve_falls_back_to_username` | override=None, display_name=None → returns username. |
| `test_resolve_final_fallback_logs_warning` | All three None → returns "Member"; assert log line `member.display_name_all_null` emitted. |
| `test_resolve_empty_override_falls_through` | override="" → falls through to user.display_name. |
| `test_resolve_avatar_color_from_user_only` | `member.display_name_override` doesn't affect `avatar_color`. |
| `test_batch_preserves_order` | `resolve_member_out_batch([(m1,u1), (m2,u2)])` returns in input order. |
| `test_batch_empty_returns_empty_list` | `[]` → `[]`. |

**Manual QA:** N/A — pure pure-function helper.

**Structured-log lines:**

| Event | Fields |
|---|---|
| `member.display_name_all_null` | `member_id`, `user_id` (WARNING; should never trigger in correct app state) |

## 8. Out of scope

| Item | Where |
|---|---|
| Per-group avatar color | OQ-07 — accepted as is for v1. |
| Display-name uniqueness | Out (PRD § 8 OQ-3). |

## 9. Structured-log events

(See § 7.)

## 10. Rollback plan

Revert. Callers must inline the COALESCE — manageable but error-prone, which is why the helper exists. No data is lost.
