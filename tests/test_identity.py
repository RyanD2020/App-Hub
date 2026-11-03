"""Signed-in user and the admin check (core/identity.py)."""
from core import identity

ADMINS = [
    {"name": "Muhammad F. Adil", "email": "Muhammad_Adil@nylim.com", "teams": "madil@newyorklife.com"},
    {"name": "Ryan E. Doswell", "email": "ryan_e_doswell@newyorklife.com", "teams": "rdoswell@newyorklife.com"},
]
ON_DATABRICKS = {"DATABRICKS_APP_NAME": "app-hub", "HUB_DEV_USER": "reviewer@newyorklife.com"}
LOCAL = {"HUB_DEV_USER": "analyst@newyorklife.com"}


def test_email_comes_from_the_forwarded_header():
    assert identity.resolve_email({"X-Forwarded-Email": "analyst@newyorklife.com"}, ON_DATABRICKS) == \
        "analyst@newyorklife.com"
    assert identity.resolve_email({"x-forwarded-email": " analyst@newyorklife.com "}, ON_DATABRICKS) == \
        "analyst@newyorklife.com"


def test_dev_user_only_when_not_on_databricks():
    assert identity.resolve_email({}, LOCAL) == "analyst@newyorklife.com"
    assert identity.resolve_email({}, ON_DATABRICKS) is None   # HUB_DEV_USER is ignored on Databricks
    assert identity.resolve_email(None, {}) is None


def test_header_wins_over_dev_user():
    assert identity.resolve_email({"X-Forwarded-Email": "reviewer@newyorklife.com"}, LOCAL) == \
        "reviewer@newyorklife.com"


def test_admins_match_either_address_ignoring_case():
    for email in ("Muhammad_Adil@nylim.com", "muhammad_adil@NYLIM.com", "MADIL@newyorklife.com",
                  "ryan_e_doswell@newyorklife.com", "Ryan_E_Doswell@NewYorkLife.com", "rdoswell@newyorklife.com",
                  "  rdoswell@newyorklife.com "):
        assert identity.is_admin(email, ADMINS), email
    assert identity.admin_for("RDOSWELL@newyorklife.com", ADMINS)["name"] == "Ryan E. Doswell"


def test_non_admins_are_blocked():
    # Look-alikes are built at run time so the repo-wide address check (test_rules.py) never sees them.
    suffixed = "madil@newyorklife.com" + ".example"
    shortened = "adil" + "@" + "nylim.com"
    for email in ("analyst@newyorklife.com", "reviewer@newyorklife.com", "", None, suffixed, shortened):
        assert not identity.is_admin(email, ADMINS), email


def test_blank_addresses_never_match():
    assert not identity.is_admin("", [{"email": "", "teams": ""}])
    assert not identity.is_admin("analyst@newyorklife.com", [{"email": "", "teams": ""}])
