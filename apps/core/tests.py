"""
UAT: Core — Auth, Hub & Multi-System Access
Test IDs: CORE-01 … CORE-15
"""
from django.contrib.auth.models import Group, User
from django.test import TestCase, Client

from apps.core.access import SYSTEMS, user_can_access, accessible_systems
from apps.core.test_utils import make_user


class CORE01_UnauthRedirectTests(TestCase):
    """Unauthenticated requests hit login redirect."""

    def setUp(self):
        self.c = Client()

    def test_hub_redirects_to_login(self):
        """CORE-01 Hub / unauthenticated → redirect to /accounts/login/?next=/"""
        r = self.c.get("/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/accounts/login/", r["Location"])

    def test_producttest_redirects_to_login(self):
        """CORE-02 /producttest/ unauthenticated → redirect"""
        r = self.c.get("/producttest/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("next=", r["Location"])

    def test_clearance_redirects_to_login(self):
        """CORE-03 /clearance/ unauthenticated → redirect"""
        r = self.c.get("/clearance/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("next=", r["Location"])

    def test_graphicqueue_redirects_to_login(self):
        """CORE-04 /graphicqueue/ unauthenticated → redirect"""
        r = self.c.get("/graphicqueue/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("next=", r["Location"])


class CORE05_NoGroupForbiddenTests(TestCase):
    """Authenticated user with no groups → 403 on all systems."""

    def setUp(self):
        self.user = make_user("nogroup_user")
        self.c = Client()
        self.c.login(username="nogroup_user", password="testpass123")

    def test_producttest_forbidden(self):
        """CORE-05 No groups → /producttest/ returns 403"""
        r = self.c.get("/producttest/")
        self.assertEqual(r.status_code, 403)

    def test_clearance_forbidden(self):
        """CORE-06 No groups → /clearance/ returns 403"""
        r = self.c.get("/clearance/")
        self.assertEqual(r.status_code, 403)

    def test_graphicqueue_forbidden(self):
        """CORE-07 No groups → /graphicqueue/ returns 403"""
        r = self.c.get("/graphicqueue/")
        self.assertEqual(r.status_code, 403)


class CORE08_PerSystemAccessTests(TestCase):
    """access_X group allows X but not Y."""

    def setUp(self):
        self.pt_user = make_user("pt_user", groups=["access_producttest"])
        self.cl_user = make_user("cl_user", groups=["access_clearance"])
        self.gq_user = make_user("gq_user", groups=["access_graphicqueue"])

    def _client(self, user):
        c = Client()
        c.login(username=user.username, password="testpass123")
        return c

    def test_producttest_user_can_access_producttest(self):
        """CORE-08a access_producttest user → /producttest/ 200"""
        r = self._client(self.pt_user).get("/producttest/")
        self.assertEqual(r.status_code, 200)

    def test_producttest_user_blocked_from_clearance(self):
        """CORE-08b access_producttest user → /clearance/ 403"""
        r = self._client(self.pt_user).get("/clearance/")
        self.assertEqual(r.status_code, 403)

    def test_producttest_user_blocked_from_graphicqueue(self):
        """CORE-08c access_producttest user → /graphicqueue/ 403"""
        r = self._client(self.pt_user).get("/graphicqueue/")
        self.assertEqual(r.status_code, 403)

    def test_clearance_user_can_access_clearance(self):
        """CORE-09 access_clearance user → /clearance/ 200"""
        r = self._client(self.cl_user).get("/clearance/")
        self.assertEqual(r.status_code, 200)

    def test_graphicqueue_user_can_access_graphicqueue(self):
        """CORE-10 access_graphicqueue user → /graphicqueue/ 200"""
        r = self._client(self.gq_user).get("/graphicqueue/")
        self.assertEqual(r.status_code, 200)


class CORE11_SuperuserAccessTests(TestCase):
    """Superuser bypasses all group checks."""

    def setUp(self):
        self.superuser = make_user("su", superuser=True)
        self.c = Client()
        self.c.login(username="su", password="testpass123")

    def test_superuser_producttest(self):
        """CORE-11a Superuser → /producttest/ 200"""
        r = self.c.get("/producttest/")
        self.assertEqual(r.status_code, 200)

    def test_superuser_clearance(self):
        """CORE-11b Superuser → /clearance/ 200"""
        r = self.c.get("/clearance/")
        self.assertEqual(r.status_code, 200)

    def test_superuser_graphicqueue(self):
        """CORE-11c Superuser → /graphicqueue/ 200"""
        r = self.c.get("/graphicqueue/")
        self.assertEqual(r.status_code, 200)


class CORE12_HubCardTests(TestCase):
    """Hub shows exactly the systems a user may access."""

    def test_hub_no_groups_shows_no_cards(self):
        """CORE-12a No-group user → hub shows 0 system cards"""
        user = make_user("hub_nogroup")
        c = Client()
        c.login(username="hub_nogroup", password="testpass123")
        r = c.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.context["systems"]), 0)

    def test_hub_one_group_shows_one_card(self):
        """CORE-12b access_producttest user → hub shows 1 card"""
        user = make_user("hub_pt", groups=["access_producttest"])
        c = Client()
        c.login(username="hub_pt", password="testpass123")
        r = c.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.context["systems"]), 1)
        self.assertEqual(r.context["systems"][0]["key"], "producttest")

    def test_hub_superuser_shows_all_cards(self):
        """CORE-12c Superuser → hub shows all 3 system cards"""
        user = make_user("hub_su", superuser=True)
        c = Client()
        c.login(username="hub_su", password="testpass123")
        r = c.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.context["systems"]), 3)


class CORE13_AccessHelpersUnitTests(TestCase):
    """Unit tests for user_can_access / accessible_systems."""

    def test_unauthenticated_user_cannot_access(self):
        """CORE-13a AnonymousUser → user_can_access returns False"""
        from django.contrib.auth.models import AnonymousUser
        anon = AnonymousUser()
        self.assertFalse(user_can_access(anon, "producttest"))

    def test_unknown_system_key_returns_false(self):
        """CORE-13b Unknown key → user_can_access returns False (not error)"""
        user = make_user("acc_unit")
        self.assertFalse(user_can_access(user, "does_not_exist"))

    def test_superuser_can_access_all_systems(self):
        """CORE-13c Superuser → accessible_systems returns all keys"""
        su = make_user("su2", superuser=True)
        systems = accessible_systems(su)
        keys = {s["key"] for s in systems}
        expected = {s["key"] for s in SYSTEMS}
        self.assertEqual(keys, expected)

    def test_systems_registry_integrity(self):
        """CORE-13d Every SYSTEMS entry has required keys"""
        required = {"key", "name", "name_th", "icon", "color", "url_name", "group"}
        for s in SYSTEMS:
            missing = required - s.keys()
            self.assertFalse(missing, f"SYSTEMS entry '{s.get('key')}' missing: {missing}")


class CORE14_LoginTests(TestCase):
    """Login / logout flow."""

    def setUp(self):
        self.user = make_user("logintest")
        self.c = Client()

    def test_login_page_200(self):
        """CORE-14a GET /accounts/login/ → 200"""
        r = self.c.get("/accounts/login/")
        self.assertEqual(r.status_code, 200)

    def test_valid_login_redirects_to_hub(self):
        """CORE-14b POST valid credentials → redirect (to /)"""
        r = self.c.post("/accounts/login/", {"username": "logintest", "password": "testpass123"})
        self.assertEqual(r.status_code, 302)

    def test_invalid_login_rerenders_form(self):
        """CORE-14c POST bad password → 200 (re-render with error)"""
        r = self.c.post("/accounts/login/", {"username": "logintest", "password": "wrongpass"})
        self.assertEqual(r.status_code, 200)

    def test_logout_redirects_to_login(self):
        """CORE-14d POST /accounts/logout/ → redirect to /accounts/login/"""
        self.c.login(username="logintest", password="testpass123")
        r = self.c.post("/accounts/logout/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/accounts/login/", r["Location"])


class CORE15_SetupGroupsTests(TestCase):
    """setup_groups management command creates all expected groups, idempotent."""

    def test_setup_groups_creates_all_groups(self):
        """CORE-15a setup_groups creates the 5 standard groups"""
        from django.core.management import call_command
        call_command("setup_groups", verbosity=0)
        expected = ["employee", "supervisor", "access_producttest", "access_clearance", "access_graphicqueue"]
        for name in expected:
            self.assertTrue(Group.objects.filter(name=name).exists(), f"Group '{name}' not created")

    def test_setup_groups_is_idempotent(self):
        """CORE-15b Running setup_groups twice does not raise or duplicate"""
        from django.core.management import call_command
        call_command("setup_groups", verbosity=0)
        call_command("setup_groups", verbosity=0)  # second run should be safe
        expected = ["employee", "supervisor", "access_producttest", "access_clearance", "access_graphicqueue"]
        for name in expected:
            self.assertEqual(Group.objects.filter(name=name).count(), 1)
