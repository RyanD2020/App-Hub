"""Who is signed in, and whether they're an admin.

On Databricks Apps the workspace signs the user in and forwards their email in the X-Forwarded-Email header. That is
the only identity the app trusts: an email typed into a form is never used to decide who someone is.
HUB_DEV_USER is a fallback for local runs only and is ignored when the app runs on Databricks.
"""
from __future__ import annotations

import os
from collections.abc import Iterable, Mapping

EMAIL_HEADER = "X-Forwarded-Email"
DEV_USER_ENV = "HUB_DEV_USER"
# Set by Databricks Apps in every app's environment.
DATABRICKS_APP_ENV = ("DATABRICKS_APP_NAME", "DATABRICKS_APP_PORT")


def on_databricks(env: Mapping[str, str] | None = None) -> bool:
    env = os.environ if env is None else env
    return any(env.get(k) for k in DATABRICKS_APP_ENV)


def resolve_email(headers: Mapping[str, str] | None, env: Mapping[str, str] | None = None) -> str | None:
    """The signed-in user's email from the request headers; HUB_DEV_USER only when not on Databricks."""
    env = os.environ if env is None else env
    value = None
    if headers:
        value = headers.get(EMAIL_HEADER)
        if value is None:  # header names are case-insensitive; plain dicts in tests aren't
            value = next((v for k, v in headers.items() if k.lower() == EMAIL_HEADER.lower()), None)
    value = (value or "").strip()
    if value:
        return value
    if not on_databricks(env):
        return (env.get(DEV_USER_ENV) or "").strip() or None
    return None


def signed_in_email() -> str | None:
    """For the running Streamlit app."""
    import streamlit as st

    try:
        headers = st.context.headers
    except Exception:
        headers = None
    return resolve_email(headers)


def admin_for(email: str | None, admins: Iterable[Mapping[str, str]]) -> Mapping[str, str] | None:
    """The admin entry matching this email on either their email or Teams address, ignoring case; else None."""
    if not email:
        return None
    wanted = email.strip().casefold()
    for a in admins:
        if wanted in {(a.get("email") or "").strip().casefold(), (a.get("teams") or "").strip().casefold()} - {""}:
            return a
    return None


def is_admin(email: str | None, admins: Iterable[Mapping[str, str]]) -> bool:
    return admin_for(email, admins) is not None
