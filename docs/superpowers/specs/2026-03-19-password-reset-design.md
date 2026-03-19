# Password Reset — Design Spec

**Date:** 2026-03-19
**Status:** Approved

---

## Overview

Add a password-reset flow accessible from the login page. The user enters their email, receives a 6-digit code, enters the code, then sets a new password. On success they are redirected to the login form (not auto-logged in).

---

## Backend

### DB change — `email_verification_codes.purpose`

Add column `purpose VARCHAR(32) DEFAULT 'email_verification' NOT NULL` via a new `ensure_email_code_purpose_column()` call in `database.py`, invoked from `init_db()`. Existing rows default to `'email_verification'`.

### `_create_verification_code()` changes

The helper gets an optional `purpose: str = 'email_verification'` parameter.

**All existing queries inside this function must be filtered by `purpose`:**
- The `recent_sends` count query: filter by `purpose` so that password-reset rate limits are tracked independently from email-verification rate limits.
- The `latest_code` cooldown query: filter by `purpose` and `used_at.is_(None)` so an active email-verification code does not absorb the cooldown window for a password-reset request.
- The new code row: write the `purpose` value.

### New Pydantic request models

```python
class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class VerifyResetCodeRequest(BaseModel):
    email: EmailStr
    code: str

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        code = value.strip()
        if not code.isdigit() or len(code) != 6:
            raise ValueError("Code must be exactly 6 digits.")
        return code

class ResetPasswordRequest(BaseModel):
    reset_token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters.")
        if len(value.encode("utf-8")) > 1024:
            raise ValueError("Password must be at most 1024 bytes.")
        return value
```

### New endpoints

#### `POST /api/auth/forgot-password`
```
Request:  ForgotPasswordRequest
Response: 200 { "status": "ok" }
```
- Looks up user by email. If not found, returns 200 with the same response (no account enumeration).
- If found, calls `_create_verification_code(db, user, purpose='password_reset')`.
- Does NOT require `email_verified_at`.
- No `message` field in the response — the frontend displays a static i18n string.

#### `POST /api/auth/verify-reset-code`
```
Request:  VerifyResetCodeRequest
Response: 200 { "reset_token": "<jwt>" }
```
- Finds active (unused, unexpired) code with `purpose='password_reset'` for this email.
- Validates HMAC, increments attempts on failure (same logic as `/verify-email`).
- On success: marks code as used (`used_at = now`), then issues a short-lived JWT:
  ```python
  create_access_token(
      data={"sub": str(user.id), "purpose": "password_reset"},
      expires_delta=timedelta(minutes=15),
  )
  ```
  The explicit `expires_delta=timedelta(minutes=15)` **must** be passed; the default is 7 days.
- Returns `{ "reset_token": "<jwt>" }`.

#### `POST /api/auth/reset-password`
```
Request:  ResetPasswordRequest
Response: 200 { "status": "ok" }
```
- Decodes and validates the `reset_token` JWT:
  - Checks signature and expiry (reuse `decode_token()`).
  - Checks `payload["purpose"] == "password_reset"` — raises 400 if missing or wrong.
- Updates `user.hashed_password = get_password_hash(new_password)`.
- Marks all remaining active `purpose='password_reset'` codes for this user as used (`used_at = now`), to prevent code reuse after the password has been changed.
- Returns `{ "status": "ok" }`.
- **Replay protection note:** the `reset_token` JWT is stateless and not stored server-side. Replay within the 15-minute window would set the password to the same value the attacker already knows — the attack value is low. A full jti denylist is out of scope.

### Email

Reuses `send_verification_code_email()`. The email subject/body is the same generic code email ("verify your email"). This is a known limitation — acceptable for the current scope; a future improvement would add a `purpose` parameter to the email function to tailor the subject/body for password reset.

---

## Frontend

### Mode extension

`auth-page.component.ts` — `mode` type extended:
```
'login' | 'register' | 'verify' | 'forgot' | 'reset-verify' | 'reset-password'
```

New transient state fields:
```ts
pendingResetEmail = '';   // set after forgot step
resetToken = '';          // set after reset-verify step
```

Both are stored in component state only (not localStorage). If the page is refreshed, the state is lost — `ngOnInit` must check `this.resetToken` / `this.pendingResetEmail` and redirect to `mode = 'login'` if absent (i.e., the component initializes in `'login'` mode by default, so this is already handled).

### New forms

```ts
readonly forgotForm = this.fb.nonNullable.group({
  email: ['', [Validators.required, Validators.email]],
});

readonly resetPasswordForm = this.fb.nonNullable.group({
  password: ['', [Validators.required, Validators.minLength(8)]],
  confirmPassword: ['', [Validators.required]],
});
```

`reset-verify` step reuses the existing `verifyForm` (6-digit OTP).

### Navigation

| From | Action | To | Side effects |
|------|--------|----|--------------|
| `login` | click "¿Olvidaste tu contraseña?" | `forgot` | clear errors |
| `forgot` | submit success | `reset-verify` | set `pendingResetEmail` |
| `reset-verify` | submit success | `reset-password` | set `resetToken` |
| `reset-password` | submit success | `login` | show `infoMessage` = `AUTH.RESET_PASSWORD_SUCCESS` |
| any reset step | click back button | `login` | clear `pendingResetEmail`, `resetToken`, errors |

**Password mismatch:** `submitResetPassword()` checks `password !== confirmPassword` before calling the API and sets `errorMessage = translate.instant('ERRORS.RESET_PASSWORD_MISMATCH')`.

**Resend on `reset-verify` step:** show a "Reenviar código" button (same pattern as the email-verification `verify` step). It calls `forgotPassword({ email: pendingResetEmail })` again. The backend rate limiting applies.

### `AUTH.RESET_CODE_SENT` usage

Displayed as `infoMessage` after:
1. The `forgot` form is submitted successfully.
2. The resend button on `reset-verify` is clicked successfully.

### `AuthService` additions

```ts
forgotPassword(payload: { email: string }): Observable<{ status: string }>
// POST /auth/forgot-password

verifyResetCode(payload: { email: string; code: string }): Observable<{ reset_token: string }>
// POST /auth/verify-reset-code

resetPassword(payload: { reset_token: string; new_password: string }): Observable<{ status: string }>
// POST /auth/reset-password
```

### i18n keys (es.json, en.json, ru.json)

```
AUTH.WELCOME_FORGOT            — subtitle on forgot step
AUTH.WELCOME_RESET_VERIFY      — subtitle on reset-verify step
AUTH.WELCOME_RESET_PASSWORD    — subtitle on reset-password step
AUTH.FORGOT_LINK               — "¿Olvidaste tu contraseña?" link text on login form
AUTH.FORGOT_BUTTON             — "Enviar código" button
AUTH.FORGOT_SENDING            — "Enviando..." loading state
AUTH.RESET_VERIFY_BUTTON       — "Verificar código" button
AUTH.RESET_VERIFYING           — "Verificando..." loading state
AUTH.RESET_PASSWORD_NEW        — "Nueva contraseña" label
AUTH.RESET_PASSWORD_CONFIRM    — "Confirmar contraseña" label
AUTH.RESET_PASSWORD_BUTTON     — "Guardar contraseña" button
AUTH.RESET_PASSWORD_SAVING     — "Guardando..." loading state
AUTH.RESET_CODE_SENT           — "Código enviado a {{email}}." (success toast after forgot + resend)
AUTH.RESET_PASSWORD_SUCCESS    — "Contraseña actualizada. Inicia sesión." (shown on login form after reset)
ERRORS.AUTH_FORGOT_FAILED      — generic forgot error
ERRORS.AUTH_RESET_VERIFY_FAILED — generic verify-code error
ERRORS.AUTH_RESET_PASSWORD_FAILED — generic reset-password error
ERRORS.RESET_PASSWORD_MISMATCH — "Las contraseñas deben coincidir."
```

---

## Security notes

- `reset_token` is a signed JWT with `purpose` claim — cannot be used as a login token.
- No account enumeration on `forgot-password` endpoint.
- Reset codes share per-purpose rate limiting (6/hour, 60s cooldown) independently from email-verification codes.
- `purpose` column prevents cross-use of verification and reset codes.
- `reset_token` stored only in component state — gone on page refresh.
- Active reset codes are invalidated after successful password reset.
- Replay protection: out of scope (low risk given 15-min window + password already changed).

---

## Out of scope

- Invalidating existing user sessions after password reset (sessions not tracked server-side).
- Password strength requirements beyond existing 8-char minimum.
- Tailored email subject/body for password reset (future improvement).
- jti denylist for reset tokens.
