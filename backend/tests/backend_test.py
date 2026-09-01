"""LogiSource backend end-to-end tests.

Run with:
    pytest /app/backend/tests/backend_test.py -v --tb=short \
        --junitxml=/app/test_reports/pytest/pytest_results.xml
"""
import io
import os
import time
from datetime import datetime, timezone, timedelta

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://logisource-build.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "admin@logisource.com"
ADMIN_PASSWORD = "Admin@12345"
STAFF_EMAIL = "staff@logisource.com"
STAFF_PASSWORD = "Staff@12345"


# ---------- shared session with token ----------
def _login(email: str, password: str) -> str:
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def admin_token():
    return _login(ADMIN_EMAIL, ADMIN_PASSWORD)


@pytest.fixture(scope="session")
def staff_token():
    return _login(STAFF_EMAIL, STAFF_PASSWORD)


@pytest.fixture(scope="session")
def admin_client(admin_token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def staff_client(staff_token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {staff_token}", "Content-Type": "application/json"})
    return s


# =========================================================
# AUTH
# =========================================================
class TestAuth:
    def test_health(self):
        r = requests.get(f"{BASE_URL}/api/health", timeout=15)
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_login_admin(self):
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data and len(data["access_token"]) > 20
        assert data["user"]["email"] == ADMIN_EMAIL
        assert data["user"]["role"] == "admin"
        assert "password_hash" not in data["user"]

    def test_login_staff(self):
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"email": STAFF_EMAIL, "password": STAFF_PASSWORD})
        assert r.status_code == 200
        assert r.json()["user"]["role"] == "staff"

    def test_login_invalid_password(self):
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"email": ADMIN_EMAIL, "password": "wrong-password"})
        assert r.status_code == 401

    def test_me_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 401

    def test_me_with_bearer(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200
        assert r.json()["email"] == ADMIN_EMAIL

    def test_change_password_wrong_old(self, admin_client):
        r = admin_client.post(f"{BASE_URL}/api/auth/change-password",
                              json={"old_password": "wrong", "new_password": "abcdef"})
        assert r.status_code == 400

    def test_change_password_roundtrip(self):
        # login as staff, change password to something new, then change it back
        tok = _login(STAFF_EMAIL, STAFF_PASSWORD)
        s = requests.Session()
        s.headers.update({"Authorization": f"Bearer {tok}"})
        r = s.post(f"{BASE_URL}/api/auth/change-password",
                   json={"old_password": STAFF_PASSWORD, "new_password": "Temp@98765"})
        assert r.status_code == 200
        # verify new password works
        r2 = requests.post(f"{BASE_URL}/api/auth/login",
                           json={"email": STAFF_EMAIL, "password": "Temp@98765"})
        assert r2.status_code == 200
        # revert
        tok2 = r2.json()["access_token"]
        s2 = requests.Session()
        s2.headers.update({"Authorization": f"Bearer {tok2}"})
        r3 = s2.post(f"{BASE_URL}/api/auth/change-password",
                     json={"old_password": "Temp@98765", "new_password": STAFF_PASSWORD})
        assert r3.status_code == 200


# =========================================================
# CUSTOMERS
# =========================================================
class TestCustomers:
    created_id = None
    created_code = None

    def test_create_customer(self, admin_client):
        r = admin_client.post(f"{BASE_URL}/api/customers",
                              json={"company_name": "TEST_Acme Corp", "email": "acme@test.com",
                                    "phone": "+62-1234", "pic_name": "John"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["company_name"] == "TEST_Acme Corp"
        assert d["code"].startswith("CUS-")
        assert d["id"]
        TestCustomers.created_id = d["id"]
        TestCustomers.created_code = d["code"]

    def test_get_customer(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/customers/{TestCustomers.created_id}")
        assert r.status_code == 200
        assert r.json()["code"] == TestCustomers.created_code

    def test_list_pagination_and_query(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/customers?q=TEST_Acme&page=1&per_page=5")
        assert r.status_code == 200
        data = r.json()
        assert "items" in data and "total" in data and "page" in data
        assert any(x["id"] == TestCustomers.created_id for x in data["items"])

    def test_update_customer(self, admin_client):
        r = admin_client.put(f"{BASE_URL}/api/customers/{TestCustomers.created_id}",
                             json={"phone": "+62-9999"})
        assert r.status_code == 200
        assert r.json()["phone"] == "+62-9999"
        # verify persistence
        r2 = admin_client.get(f"{BASE_URL}/api/customers/{TestCustomers.created_id}")
        assert r2.json()["phone"] == "+62-9999"

    def test_staff_can_create_but_not_delete(self, staff_client, admin_client):
        r = staff_client.post(f"{BASE_URL}/api/customers",
                              json={"company_name": "TEST_Staff Created"})
        assert r.status_code == 200
        sid = r.json()["id"]
        # staff delete forbidden
        r2 = staff_client.delete(f"{BASE_URL}/api/customers/{sid}")
        assert r2.status_code == 403
        # admin can delete
        r3 = admin_client.delete(f"{BASE_URL}/api/customers/{sid}")
        assert r3.status_code == 200

    def test_export_import_xlsx_roundtrip(self, admin_client):
        # export
        r = requests.get(f"{BASE_URL}/api/customers/export/xlsx",
                         headers={"Authorization": admin_client.headers["Authorization"]})
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("application/vnd.openxmlformats")
        assert len(r.content) > 200
        # attempt import (uses same file — most rows will be skipped as codes exist)
        files = {"file": ("customers.xlsx", r.content,
                          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        r2 = requests.post(f"{BASE_URL}/api/customers/import/xlsx", files=files,
                           headers={"Authorization": admin_client.headers["Authorization"]})
        assert r2.status_code == 200, r2.text
        j = r2.json()
        assert "created" in j and "skipped" in j


# =========================================================
# PRODUCTS
# =========================================================
class TestProducts:
    goods_id = None
    service_id = None
    cat_id = None

    def test_create_category(self, admin_client):
        name = f"TEST_Cat_{int(time.time())}"
        r = admin_client.post(f"{BASE_URL}/api/products/categories", json={"name": name})
        assert r.status_code == 200, r.text
        TestProducts.cat_id = r.json()["id"]
        assert r.json()["name"] == name

    def test_list_categories(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/products/categories")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_goods(self, admin_client):
        r = admin_client.post(f"{BASE_URL}/api/products",
                              json={"name": "TEST_Widget", "product_type": "goods",
                                    "selling_price": 100000, "stock": 5})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["code"].startswith("PRD-")
        assert d["product_type"] == "goods"
        TestProducts.goods_id = d["id"]

    def test_create_service(self, admin_client):
        r = admin_client.post(f"{BASE_URL}/api/products",
                              json={"name": "TEST_Support", "product_type": "service",
                                    "selling_price": 500000, "sla": "24x7"})
        assert r.status_code == 200
        d = r.json()
        assert d["code"].startswith("SRV-")
        TestProducts.service_id = d["id"]

    def test_filter_by_type(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/products?product_type=service&per_page=100")
        assert r.status_code == 200
        for it in r.json()["items"]:
            assert it["product_type"] == "service"

    def test_export_pdf(self, admin_client):
        r = requests.get(f"{BASE_URL}/api/products/export/pdf",
                         headers={"Authorization": admin_client.headers["Authorization"]})
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("application/pdf")
        assert r.content[:4] == b"%PDF"

    def test_export_xlsx_roundtrip(self, admin_client):
        r = requests.get(f"{BASE_URL}/api/products/export/xlsx",
                         headers={"Authorization": admin_client.headers["Authorization"]})
        assert r.status_code == 200
        assert len(r.content) > 200
        files = {"file": ("products.xlsx", r.content,
                          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        r2 = requests.post(f"{BASE_URL}/api/products/import/xlsx", files=files,
                           headers={"Authorization": admin_client.headers["Authorization"]})
        assert r2.status_code == 200

    def test_staff_cannot_delete_product(self, staff_client):
        r = staff_client.delete(f"{BASE_URL}/api/products/{TestProducts.goods_id}")
        assert r.status_code == 403


# =========================================================
# QUOTATIONS
# =========================================================
class TestQuotations:
    q_ids = []
    q_numbers = []

    def test_create_and_totals(self, admin_client):
        cust_id = TestCustomers.created_id
        assert cust_id, "Customer must exist"
        payload = {
            "customer_id": cust_id,
            "date": "2026-01-15",
            "items": [
                {"product_name": "Item1", "quantity": 2, "unit_price": 100, "discount_percent": 10, "tax_percent": 11},
                {"product_name": "Item2", "quantity": 1, "unit_price": 50, "discount_percent": 0, "tax_percent": 0},
            ]
        }
        r = admin_client.post(f"{BASE_URL}/api/quotations", json=payload)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["number"].startswith("QTN-")
        TestQuotations.q_ids.append(d["id"])
        TestQuotations.q_numbers.append(d["number"])

        # GET returns totals
        r2 = admin_client.get(f"{BASE_URL}/api/quotations/{d['id']}")
        assert r2.status_code == 200
        t = r2.json()["totals"]
        # subtotal: 2*100 + 1*50 = 250
        assert abs(t["subtotal"] - 250.0) < 0.01
        # discount: 200*10% = 20
        assert abs(t["discount"] - 20.0) < 0.01
        # tax: (200-20)*11% = 19.8, plus 0 = 19.8
        assert abs(t["tax"] - 19.8) < 0.01
        # total: (180+19.8) + 50 = 249.8
        assert abs(t["total"] - 249.8) < 0.01

    def test_auto_numbering_monotonic(self, admin_client):
        cust_id = TestCustomers.created_id
        for _ in range(2):
            r = admin_client.post(f"{BASE_URL}/api/quotations",
                                  json={"customer_id": cust_id, "date": "2026-01-15",
                                        "items": [{"product_name": "x", "quantity": 1, "unit_price": 10}]})
            assert r.status_code == 200
            TestQuotations.q_ids.append(r.json()["id"])
            TestQuotations.q_numbers.append(r.json()["number"])
        # Extract sequence numbers
        seqs = [int(n.split("-")[-1]) for n in TestQuotations.q_numbers]
        # Must be strictly increasing across the last three
        for a, b in zip(seqs, seqs[1:]):
            assert b > a, f"Expected monotonic sequence, got {seqs}"

    def test_status_transitions(self, admin_client):
        qid = TestQuotations.q_ids[0]
        for st in ["sent", "approved"]:
            r = admin_client.post(f"{BASE_URL}/api/quotations/{qid}/status?status={st}")
            assert r.status_code == 200, r.text
            assert r.json()["status"] == st

    def test_pdf(self, admin_client):
        qid = TestQuotations.q_ids[0]
        r = requests.get(f"{BASE_URL}/api/quotations/{qid}/pdf",
                         headers={"Authorization": admin_client.headers["Authorization"]})
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("application/pdf")
        assert r.content[:4] == b"%PDF"

    def test_staff_cannot_delete_quotation(self, staff_client):
        r = staff_client.delete(f"{BASE_URL}/api/quotations/{TestQuotations.q_ids[-1]}")
        assert r.status_code == 403


# =========================================================
# INVOICES
# =========================================================
class TestInvoices:
    inv_ids = []

    def test_create_invoice(self, admin_client):
        r = admin_client.post(f"{BASE_URL}/api/invoices",
                              json={"customer_id": TestCustomers.created_id, "date": "2026-01-15",
                                    "items": [{"product_name": "svc", "quantity": 1, "unit_price": 1000, "tax_percent": 11}]})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["number"].startswith("INV-")
        TestInvoices.inv_ids.append(d["id"])

    def test_from_quotation(self, admin_client):
        qid = TestQuotations.q_ids[0]
        r = admin_client.post(f"{BASE_URL}/api/invoices/from-quotation/{qid}")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["quotation_id"] == qid
        assert d["customer_id"] == TestCustomers.created_id
        assert len(d["items"]) >= 1
        TestInvoices.inv_ids.append(d["id"])

    def test_status_paid(self, admin_client):
        iid = TestInvoices.inv_ids[0]
        r = admin_client.post(f"{BASE_URL}/api/invoices/{iid}/status?status=paid")
        assert r.status_code == 200
        assert r.json()["status"] == "paid"

    def test_pdf(self, admin_client):
        iid = TestInvoices.inv_ids[0]
        r = requests.get(f"{BASE_URL}/api/invoices/{iid}/pdf",
                         headers={"Authorization": admin_client.headers["Authorization"]})
        assert r.status_code == 200
        assert r.content[:4] == b"%PDF"

    def test_staff_cannot_delete(self, staff_client):
        r = staff_client.delete(f"{BASE_URL}/api/invoices/{TestInvoices.inv_ids[-1]}")
        assert r.status_code == 403


# =========================================================
# PROJECTS
# =========================================================
class TestProjects:
    pid = None

    def test_create_project(self, admin_client):
        r = admin_client.post(f"{BASE_URL}/api/projects",
                              json={"name": "TEST_Proj_1",
                                    "customer_id": TestCustomers.created_id,
                                    "status": "planning"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["number"].startswith("PRJ-")
        TestProjects.pid = d["id"]

    def test_get_project_expanded(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/projects/{TestProjects.pid}")
        assert r.status_code == 200
        d = r.json()
        assert d["customer"]["id"] == TestCustomers.created_id
        assert d["products"] == []
        assert d["accounts"] == []
        assert d["licenses"] == []

    def test_link_accounts_no_password_leak(self, admin_client):
        # Create an account first with password
        ra = admin_client.post(f"{BASE_URL}/api/accounts",
                               json={"name": "TEST_ProjAcc", "category": "Custom",
                                     "password": "secret123"})
        assert ra.status_code == 200
        aid = ra.json()["id"]
        # Link it
        ru = admin_client.put(f"{BASE_URL}/api/projects/{TestProjects.pid}",
                              json={"account_ids": [aid]})
        assert ru.status_code == 200
        # Fetch project detail
        rg = admin_client.get(f"{BASE_URL}/api/projects/{TestProjects.pid}")
        assert rg.status_code == 200
        accs = rg.json()["accounts"]
        assert len(accs) == 1
        assert "password" not in accs[0], f"password leaked: {accs[0]}"
        assert "api_key" not in accs[0]
        assert "secret_key" not in accs[0]

    def test_staff_cannot_delete_project(self, staff_client):
        r = staff_client.delete(f"{BASE_URL}/api/projects/{TestProjects.pid}")
        assert r.status_code == 403


# =========================================================
# ACCOUNTS (VAULT)
# =========================================================
class TestAccounts:
    aid = None

    def test_categories_endpoint(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/accounts/categories")
        assert r.status_code == 200
        cats = r.json()
        assert isinstance(cats, list)
        assert len(cats) == 14
        for expected in ("Starlink", "Cloudflare", "MikroTik", "UniFi"):
            assert expected in cats

    def test_generate_password(self, admin_client):
        r = admin_client.post(f"{BASE_URL}/api/accounts/generate-password?length=20")
        assert r.status_code == 200
        pw = r.json()["password"]
        assert len(pw) == 20
        assert any(c.isupper() for c in pw)
        assert any(c.islower() for c in pw)
        assert any(c.isdigit() for c in pw)

    def test_create_and_list_no_password(self, admin_client):
        r = admin_client.post(f"{BASE_URL}/api/accounts",
                              json={"name": "TEST_Vault", "category": "Cloudflare",
                                    "username": "admin", "password": "SuperSecret!23",
                                    "api_key": "APIKEY-XYZ"})
        assert r.status_code == 200, r.text
        d = r.json()
        TestAccounts.aid = d["id"]
        # Response must be masked
        assert "password" not in d
        assert d.get("has_password") is True
        assert d.get("has_api_key") is True
        assert d.get("has_secret_key") is False

        # LIST must also be masked — no ciphertext / plaintext
        rl = admin_client.get(f"{BASE_URL}/api/accounts?per_page=100")
        assert rl.status_code == 200
        found = [x for x in rl.json()["items"] if x["id"] == TestAccounts.aid]
        assert found
        assert "password" not in found[0]
        assert "api_key" not in found[0]
        assert found[0]["has_password"] is True

    def test_reveal_roundtrip(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/accounts/{TestAccounts.aid}/reveal")
        assert r.status_code == 200
        d = r.json()
        assert d["password"] == "SuperSecret!23"
        assert d["api_key"] == "APIKEY-XYZ"

    def test_update_empty_password_preserved(self, admin_client):
        """Update with password='' must NOT overwrite the existing password."""
        r = admin_client.put(f"{BASE_URL}/api/accounts/{TestAccounts.aid}",
                             json={"name": "TEST_Vault_Renamed", "password": ""})
        assert r.status_code == 200
        # Reveal again — password should still be SuperSecret!23
        r2 = admin_client.get(f"{BASE_URL}/api/accounts/{TestAccounts.aid}/reveal")
        assert r2.status_code == 200
        assert r2.json()["password"] == "SuperSecret!23", (
            f"Empty password overwrote existing! got={r2.json()['password']!r}")

    def test_update_new_password_replaces(self, admin_client):
        r = admin_client.put(f"{BASE_URL}/api/accounts/{TestAccounts.aid}",
                             json={"password": "NewPass!456"})
        assert r.status_code == 200
        r2 = admin_client.get(f"{BASE_URL}/api/accounts/{TestAccounts.aid}/reveal")
        assert r2.json()["password"] == "NewPass!456"

    def test_staff_cannot_delete_account(self, staff_client):
        r = staff_client.delete(f"{BASE_URL}/api/accounts/{TestAccounts.aid}")
        assert r.status_code == 403


# =========================================================
# LICENSES
# =========================================================
class TestLicenses:
    lid_soon = None
    lid_far = None

    def test_create_licenses(self, admin_client):
        soon = (datetime.now(timezone.utc) + timedelta(days=15)).date().isoformat()
        far = (datetime.now(timezone.utc) + timedelta(days=180)).date().isoformat()
        r1 = admin_client.post(f"{BASE_URL}/api/licenses",
                               json={"license_code": "TEST_LIC_SOON", "product_name": "P1",
                                     "expiry_date": soon})
        r2 = admin_client.post(f"{BASE_URL}/api/licenses",
                               json={"license_code": "TEST_LIC_FAR", "product_name": "P2",
                                     "expiry_date": far})
        assert r1.status_code == 200 and r2.status_code == 200
        TestLicenses.lid_soon = r1.json()["id"]
        TestLicenses.lid_far = r2.json()["id"]

    def test_within_days_filter(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/licenses?within_days=30&per_page=200")
        assert r.status_code == 200
        codes = [x["license_code"] for x in r.json()["items"]]
        assert "TEST_LIC_SOON" in codes
        assert "TEST_LIC_FAR" not in codes

    def test_days_left(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/licenses/{TestLicenses.lid_soon}")
        assert r.status_code == 200
        dl = r.json()["days_left"]
        assert dl is not None and 10 <= dl <= 20

    def test_staff_cannot_delete_license(self, staff_client):
        r = staff_client.delete(f"{BASE_URL}/api/licenses/{TestLicenses.lid_soon}")
        assert r.status_code == 403


# =========================================================
# USERS (admin only)
# =========================================================
class TestUsers:
    uid_new = None

    def test_staff_403(self, staff_client):
        r = staff_client.get(f"{BASE_URL}/api/users")
        assert r.status_code == 403

    def test_admin_can_list(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/users")
        assert r.status_code == 200

    def test_admin_can_create_and_update(self, admin_client):
        email = f"TEST_user_{int(time.time())}@example.com"
        r = admin_client.post(f"{BASE_URL}/api/users",
                              json={"name": "TestUser", "email": email,
                                    "password": "abc123", "role": "staff"})
        assert r.status_code == 200, r.text
        TestUsers.uid_new = r.json()["id"]
        r2 = admin_client.put(f"{BASE_URL}/api/users/{TestUsers.uid_new}",
                              json={"name": "TestUser Updated"})
        assert r2.status_code == 200
        assert r2.json()["name"] == "TestUser Updated"

    def test_admin_cannot_delete_self(self, admin_client):
        me = admin_client.get(f"{BASE_URL}/api/auth/me").json()
        r = admin_client.delete(f"{BASE_URL}/api/users/{me['id']}")
        assert r.status_code == 400

    def test_admin_can_delete_user(self, admin_client):
        r = admin_client.delete(f"{BASE_URL}/api/users/{TestUsers.uid_new}")
        assert r.status_code == 200


# =========================================================
# SETTINGS
# =========================================================
class TestSettings:
    def test_get_settings_defaults(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/settings")
        assert r.status_code == 200
        d = r.json()
        assert d.get("company_name") == "LogiSource Digital"
        assert d.get("currency") == "IDR"

    def test_admin_update_settings(self, admin_client):
        r = admin_client.put(f"{BASE_URL}/api/settings", json={"company_phone": "+62-777-777"})
        assert r.status_code == 200
        assert r.json()["company_phone"] == "+62-777-777"

    def test_staff_403_on_put(self, staff_client):
        r = staff_client.put(f"{BASE_URL}/api/settings", json={"company_phone": "hack"})
        assert r.status_code == 403

    def test_staff_403_on_backup(self, staff_client):
        r = staff_client.get(f"{BASE_URL}/api/settings/backup")
        assert r.status_code == 403

    def test_admin_backup(self, admin_client):
        r = requests.get(f"{BASE_URL}/api/settings/backup",
                         headers={"Authorization": admin_client.headers["Authorization"]})
        assert r.status_code == 200
        import json as _json
        body = _json.loads(r.content)
        assert "collections" in body


# =========================================================
# ACTIVITY LOGS
# =========================================================
class TestActivityLogs:
    def test_list_and_desc_order(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/activity-logs?per_page=50")
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) > 0
        # ensure timestamps descending
        for a, b in zip(items, items[1:]):
            assert a["timestamp"] >= b["timestamp"]
        # login must be recorded
        actions = {x["action"] for x in items}
        assert "login" in actions or any("login" in a for a in actions)


# =========================================================
# DASHBOARD
# =========================================================
class TestDashboard:
    def test_summary(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/dashboard/summary")
        assert r.status_code == 200
        d = r.json()
        for k in ("counts", "alerts", "charts", "recent_activity"):
            assert k in d
        for k in ("customers", "products", "projects", "quotations", "invoices",
                  "accounts", "licenses", "users"):
            assert k in d["counts"]
        for k in ("licenses_30d", "licenses_7d", "registrations_30d", "unpaid_invoices"):
            assert k in d["alerts"]
        for k in ("monthly_quotations", "monthly_invoices", "monthly_customers"):
            assert k in d["charts"]
            assert len(d["charts"][k]) == 12


# =========================================================
# RBAC final sweep
# =========================================================
class TestRBACFinal:
    def test_staff_cannot_delete_customer(self, staff_client, admin_client):
        r = staff_client.delete(f"{BASE_URL}/api/customers/{TestCustomers.created_id}")
        assert r.status_code == 403


# =========================================================
# Cleanup — best-effort, admin deletes seeded TEST_ data
# =========================================================
@pytest.fixture(scope="session", autouse=True)
def _cleanup(request, admin_token):
    yield
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {admin_token}"})
    # Delete created quotations, invoices, projects, accounts, licenses, customer, products
    for iid in TestInvoices.inv_ids:
        s.delete(f"{BASE_URL}/api/invoices/{iid}")
    for qid in TestQuotations.q_ids:
        s.delete(f"{BASE_URL}/api/quotations/{qid}")
    if TestProjects.pid:
        s.delete(f"{BASE_URL}/api/projects/{TestProjects.pid}")
    if TestAccounts.aid:
        s.delete(f"{BASE_URL}/api/accounts/{TestAccounts.aid}")
    for lid in (TestLicenses.lid_soon, TestLicenses.lid_far):
        if lid:
            s.delete(f"{BASE_URL}/api/licenses/{lid}")
    for pid in (TestProducts.goods_id, TestProducts.service_id):
        if pid:
            s.delete(f"{BASE_URL}/api/products/{pid}")
    if TestProducts.cat_id:
        s.delete(f"{BASE_URL}/api/products/categories/{TestProducts.cat_id}")
    if TestCustomers.created_id:
        s.delete(f"{BASE_URL}/api/customers/{TestCustomers.created_id}")
