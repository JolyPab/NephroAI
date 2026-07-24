import asyncio
import datetime as dt
import hashlib
import hmac

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend import auth_routes
from backend.auth_routes import SocialAuthRequest, SocialProfile, social_auth
from backend.database import AuditLog, Base, OAuthIdentity, User


def _setup_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return session()


def _credential() -> str:
    return "provider-credential-long-enough"


def test_social_register_then_login_uses_verified_provider_identity(monkeypatch):
    db = _setup_db()
    monkeypatch.setattr(
        auth_routes,
        "_verify_social_credential",
        lambda provider, _credential: SocialProfile(
            provider=provider,
            subject="google-subject-1",
            email="SOCIAL@example.com",
            full_name="Social Patient",
        ),
    )

    register_response = asyncio.run(
        social_auth(
            SocialAuthRequest(
                provider="google",
                credential=_credential(),
                action="register",
                is_doctor=False,
            ),
            db=db,
        )
    )

    assert register_response.accessToken
    assert register_response.isNewUser is True
    assert register_response.user.email == "social@example.com"
    assert register_response.user.email_verified is True
    user = db.query(User).filter(User.email == "social@example.com").one()
    assert user.is_active is True
    assert user.email_verified_at is not None
    identity = db.query(OAuthIdentity).one()
    assert identity.user_id == user.id
    assert identity.provider == "google"
    assert identity.provider_subject == "google-subject-1"

    login_response = asyncio.run(
        social_auth(
            SocialAuthRequest(
                provider="google",
                credential=_credential(),
                action="login",
            ),
            db=db,
        )
    )
    assert login_response.accessToken
    assert login_response.isNewUser is False
    assert login_response.user.id == user.id
    actions = [row.action for row in db.query(AuditLog).order_by(AuditLog.id).all()]
    assert actions == ["auth_social_register_success", "auth_social_login_success"]
    db.close()


def test_social_login_requires_prior_registration(monkeypatch):
    db = _setup_db()
    monkeypatch.setattr(
        auth_routes,
        "_verify_social_credential",
        lambda provider, _credential: SocialProfile(
            provider=provider,
            subject="facebook-subject-1",
            email="new@example.com",
            full_name="New User",
        ),
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            social_auth(
                SocialAuthRequest(
                    provider="facebook",
                    credential=_credential(),
                    action="login",
                ),
                db=db,
            )
        )

    assert exc.value.status_code == 404
    assert exc.value.detail["code"] == "social_account_not_found"
    assert db.query(User).count() == 0
    assert db.query(OAuthIdentity).count() == 0

    register_response = asyncio.run(
        social_auth(
            SocialAuthRequest(
                provider="facebook",
                credential=_credential(),
                action="register",
                is_doctor=True,
            ),
            db=db,
        )
    )
    assert register_response.isNewUser is True
    assert register_response.user.is_doctor is True
    assert db.query(User).one().is_doctor is True
    assert db.query(OAuthIdentity).one().provider == "facebook"
    db.close()


def test_social_registration_does_not_auto_link_confirmed_password_account(monkeypatch):
    db = _setup_db()
    existing = User(
        email="Existing@Example.com",
        hashed_password="password-hash",
        full_name="Existing",
        is_active=True,
        email_verified_at=dt.datetime.utcnow(),
    )
    db.add(existing)
    db.commit()
    monkeypatch.setattr(
        auth_routes,
        "_verify_social_credential",
        lambda provider, _credential: SocialProfile(
            provider=provider,
            subject="google-subject-existing",
            email="existing@example.com",
            full_name=existing.full_name,
        ),
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            social_auth(
                SocialAuthRequest(
                    provider="google",
                    credential=_credential(),
                    action="register",
                ),
                db=db,
            )
        )

    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "social_email_exists"
    assert db.query(OAuthIdentity).count() == 0
    db.close()


def test_social_registration_recovers_pending_email_account_and_role(monkeypatch):
    db = _setup_db()
    pending = User(
        email="pending@example.com",
        hashed_password="password-hash",
        full_name=None,
        is_active=False,
        email_verified_at=None,
        is_doctor=False,
    )
    db.add(pending)
    db.commit()
    monkeypatch.setattr(
        auth_routes,
        "_verify_social_credential",
        lambda provider, _credential: SocialProfile(
            provider=provider,
            subject="facebook-subject-pending",
            email=pending.email,
            full_name="Dra. Social",
        ),
    )

    response = asyncio.run(
        social_auth(
            SocialAuthRequest(
                provider="facebook",
                credential=_credential(),
                action="register",
                is_doctor=True,
            ),
            db=db,
        )
    )

    db.refresh(pending)
    assert response.isNewUser is True
    assert response.user.role == "DOCTOR"
    assert pending.is_active is True
    assert pending.email_verified_at is not None
    assert pending.is_doctor is True
    assert pending.full_name == "Dra. Social"
    assert db.query(OAuthIdentity).filter(OAuthIdentity.user_id == pending.id).count() == 1
    db.close()


def test_social_identity_cannot_restore_deactivated_account(monkeypatch):
    db = _setup_db()
    user = User(
        email="disabled@example.com",
        hashed_password="password-hash",
        full_name="Disabled",
        is_active=False,
        email_verified_at=dt.datetime.utcnow(),
    )
    db.add(user)
    db.flush()
    db.add(
        OAuthIdentity(
            user_id=user.id,
            provider="google",
            provider_subject="google-subject-disabled",
        )
    )
    db.commit()
    monkeypatch.setattr(
        auth_routes,
        "_verify_social_credential",
        lambda provider, _credential: SocialProfile(
            provider=provider,
            subject="google-subject-disabled",
            email=user.email,
            full_name=user.full_name,
        ),
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            social_auth(
                SocialAuthRequest(
                    provider="google",
                    credential=_credential(),
                    action="login",
                ),
                db=db,
            )
        )

    assert exc.value.status_code == 403
    assert exc.value.detail["code"] == "social_account_inactive"
    db.close()


def test_google_credential_verifier_checks_signed_id_token(monkeypatch):
    client_id = "google-client.apps.googleusercontent.com"
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = dt.datetime.now(dt.timezone.utc)
    credential = jwt.encode(
        {
            "iss": "https://accounts.google.com",
            "aud": client_id,
            "sub": "google-signed-subject",
            "email": "signed@example.com",
            "email_verified": True,
            "name": "Signed User",
            "iat": now,
            "exp": now + dt.timedelta(minutes=5),
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )

    class _SigningKey:
        key = private_key.public_key()

    class _JwkClient:
        @staticmethod
        def get_signing_key_from_jwt(_credential):
            return _SigningKey()

    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", client_id)
    monkeypatch.setattr(auth_routes, "_google_jwk_client", lambda: _JwkClient())

    profile = auth_routes._verify_google_credential(credential)

    assert profile.provider == "google"
    assert profile.subject == "google-signed-subject"
    assert str(profile.email) == "signed@example.com"
    assert profile.full_name == "Signed User"


def test_facebook_credential_verifier_validates_app_and_user(monkeypatch):
    app_id = "facebook-app-id"
    app_secret = "facebook-app-secret"
    credential = _credential()
    monkeypatch.setenv("FACEBOOK_APP_ID", app_id)
    monkeypatch.setenv("FACEBOOK_APP_SECRET", app_secret)

    def _fake_graph_get(path, *, access_token, params=None):
        if path == "debug_token":
            assert access_token == f"{app_id}|{app_secret}"
            assert params == {"input_token": credential}
            return {
                "data": {
                    "is_valid": True,
                    "app_id": app_id,
                    "user_id": "facebook-subject-signed",
                }
            }
        assert path == "me"
        assert access_token == credential
        assert params["fields"] == "id,name,email"
        assert params["appsecret_proof"] == hmac.new(
            app_secret.encode("utf-8"),
            credential.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return {
            "id": "facebook-subject-signed",
            "email": "facebook@example.com",
            "name": "Facebook User",
        }

    monkeypatch.setattr(auth_routes, "_facebook_graph_get", _fake_graph_get)

    profile = auth_routes._verify_facebook_credential(credential)

    assert profile.provider == "facebook"
    assert profile.subject == "facebook-subject-signed"
    assert str(profile.email) == "facebook@example.com"
    assert profile.full_name == "Facebook User"
