# BE-020 — `POST /api/users/me/devices` + `DELETE /api/users/me/devices/{device_id}` (push-token registration)

**Wave:** 2
**Type:** BE
**Blocked by:** BE-003
**Blocks:** FE-100
**ADR references:** [ADR-006 § 2.12, § 4.26](../../decisions/ADR-006-initial-data-schema.md)

## 1. Problem statement

Push notifications are deferred to v1.x, but the `device` table is in V001 so the send pipeline lands additively. v1 ships the registration plumbing only — the Expo client calls `POST /devices` on app launch + permission grant. The FE clears the registration via `DELETE` when the user toggles off notifications.

## 2. Actual solution

Two endpoints. Both auth-required.

`POST /api/users/me/devices` — body `DeviceRegisterRequest`. Idempotent on `(user_id, push_token)`. Algorithm:

1. SELECT device WHERE `(user_id, push_token)`.
2. If found: UPDATE `last_seen_at = now()`, `revoked_at = NULL` (re-activate if previously revoked). Return existing row.
3. If not found: INSERT.
4. Return `DeviceOut`.

`DELETE /api/users/me/devices/{device_id}` — sets `revoked_at = now()`. Returns `DeviceRevokeResponse`.

Optional `GET /api/users/me/devices` — list the caller's devices. **Out of scope here** (no UI uses it in v1; add to BACKLOG if FE-009 needs it).

## 3. Files to touch

| Path | Edit purpose |
|---|---|
| `services/api/app/services/device_service.py` | `register_device`, `revoke_device`. |
| `services/api/app/schemas/devices.py` | `DeviceRegisterRequest`, `DeviceOut`, `DeviceRevokeResponse`. |
| `services/api/app/routes/users.py` | Add `POST /devices` + `DELETE /devices/{device_id}` under `/api/users/me/`. |
| `services/api/tests/test_devices.py` | See § 7. |
| `docs/CODEBASE_GUIDE.md` | Add. |

## 4. Method signatures / new APIs

(From reference.)

```python
class DeviceRegisterRequest(_Model):
    platform: DevicePlatform
    push_token: str = Field(min_length=1, max_length=4096)
    push_provider: PushProvider = PushProvider.expo


class DeviceOut(_Model):
    device_id: UUID
    user_id: UUID
    platform: DevicePlatform
    push_provider: PushProvider
    created_at: datetime
    last_seen_at: datetime
    revoked_at: datetime | None


class DeviceRevokeResponse(_Model):
    device_id: UUID
    revoked_at: datetime
```

Endpoints:

| Method | Path | Body | Response | Status |
|---|---|---|---|---|
| `POST` | `/api/users/me/devices` | `DeviceRegisterRequest` | `DeviceOut` | 200 (re-register) / 201 (new) |
| `DELETE` | `/api/users/me/devices/{device_id}` | — | `DeviceRevokeResponse` | 200 |

Errors:

| HTTP | error_code | When |
|---|---|---|
| 404 | `device_not_found` | `device_id` doesn't belong to the caller. |

## 5. Constants and thresholds

| Constant | Value | Rationale |
|---|---|---|
| `push_token` max length | 4096 | Generous for Expo + APNs + FCM tokens (all < 200 in practice). |
| `push_provider` default | `expo` | ADR-006 § 4.26. |

## 6. Edge cases enumerated

| Case | Expected behavior |
|---|---|
| Re-registering the same token | UPDATE `last_seen_at`; 200. |
| Re-registering a previously revoked token | Re-activate: `revoked_at = NULL`, UPDATE `last_seen_at`. 200. |
| Registering a token already owned by a different user | Per the unique index `(user_id, push_token)`, this is allowed at the DB level (different user). In practice the same token shouldn't be on two accounts; if it is, both receive notifications. v1 doesn't deduplicate cross-user. |
| `platform="windows"` | Pydantic enum rejection → 422. |
| `push_provider="apns"` | Accepted by schema; v1 only writes `expo`. The other values exist for future migration off Expo. Defensive: allow but log INFO. |
| Revoke a `device_id` not owned by caller | 404 `device_not_found`. Don't 403 (would leak existence). |
| Revoke an already-revoked device | 200; `revoked_at` stays at the original timestamp. Idempotent. |

## 7. Acceptable validation

**Tests that MUST exist:**

| Test name | Assertion |
|---|---|
| `test_register_new_device_returns_201` | New `(user, token)` → 201; row inserted; `revoked_at=None`. |
| `test_register_idempotent_returns_200_and_bumps_last_seen` | Re-POST same token → 200; `last_seen_at` advanced. |
| `test_register_revoked_token_re_activates` | Token previously revoked → `revoked_at` becomes NULL. |
| `test_register_apns_provider_logs_unusual_value` | `push_provider="apns"` → 201; log line emitted at INFO. |
| `test_register_invalid_platform_returns_422` | `platform="windows"` → 422. |
| `test_register_unauthenticated_returns_401` | No JWT → 401. |
| `test_revoke_device_sets_revoked_at` | POST then DELETE → row has `revoked_at != None`. |
| `test_revoke_unknown_device_returns_404` | Random UUID → 404. |
| `test_revoke_other_users_device_returns_404` | User A's device; User B DELETE → 404 (not 403). |
| `test_revoke_already_revoked_is_idempotent` | DELETE → DELETE → both 200; `revoked_at` unchanged on 2nd. |

**Manual QA:**

1. As authenticated user, POST a token. Response 201.
2. POST same token. Response 200; `last_seen_at` newer.
3. DELETE the device_id. `revoked_at` set.

**Structured-log lines:**

| Event | Fields |
|---|---|
| `device.registered` | `user_id`, `device_id`, `platform`, `push_provider`, `was_revoked: bool`, `request_id` |
| `device.revoked` | `user_id`, `device_id`, `request_id` |
| `device.unusual_provider` | `user_id`, `push_provider`, `request_id` (INFO) |

## 8. Out of scope

| Item | Where |
|---|---|
| Push send pipeline | BACKLOG-018 (v1.x). |
| Token freshness sweep | v1.x. |
| APNs / FCM credential setup | v1.x. |
| Per-group notification preferences | v1.x. |

## 9. Structured-log events

(See § 7.)

## 10. Rollback plan

Revert. New devices can't register; existing rows persist. Send pipeline (v1.x) won't run yet, so no user impact.
