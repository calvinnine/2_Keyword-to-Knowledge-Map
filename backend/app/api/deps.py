"""FastAPI dependency helpers for access control.

Current model (pre-auth):
  PUBLIC_ONLY=true  → sensitive endpoints raise 403
  PUBLIC_ONLY=false → full access (use only after proper auth is in place)

Grade reference (v2.2 planning report §13):
  Public            → always accessible
  Registered        → future: login required
  Verified Prof.    → future: verified role required
  Admin/Internal    → future: admin role required
  Hidden/System-only→ never exposed via API
"""

from fastapi import Depends, HTTPException

from app.config import settings


def require_non_public() -> None:
    """Raise 403 when PUBLIC_ONLY mode is active.

    Use as a FastAPI dependency on endpoints that expose
    Registered / Verified Professional / Admin-grade data.
    """
    if settings.public_only:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "PUBLIC_ONLY",
                "message": (
                    "이 정보는 현재 공개 범위에 포함되지 않습니다. "
                    "서비스 고도화 이후 인증된 사용자에게 제공될 예정입니다."
                ),
            },
        )
