# coding=utf-8
"""Test certbot.display.ops."""
import os
import sys
import tempfile
import unittest

import mock
import zope.component

from acme import jose
from acme import messages

from certbot import account
from certbot import errors

from certbot.display import util as display_util

import certbot.tests.util as test_util


KEY = jose.JWKRSA.load(test_util.load_vector("rsa512_key.pem"))


class GetEmailTest(unittest.TestCase):
    """Tests for certbot.display.ops.get_email."""

    @classmethod
    def _call(cls, **kwargs):
        from certbot.display.ops import get_email
        return get_email(**kwargs)

    @test_util.patch_get_utility("certbot.display.ops.z_util")
    def test_cancel_none(self, mock_get_utility):
        mock_input = mock_get_utility().input
        mock_input.return_value = (display_util.CANCEL, "foo@bar.baz")
        self.assertRaises(errors.Error, self._call)
        self.assertRaises(errors.Error, self._call, optional=False)

    @test_util.patch_get_utility("certbot.display.ops.z_util")
    def test_ok_safe(self, mock_get_utility):
        mock_input = mock_get_utility().input
        mock_input.return_value = (display_util.OK, "foo@bar.baz")
        with mock.patch("certbot.display.ops.util.safe_email") as mock_safe_email:
            mock_safe_email.return_value = True
            self.assertTrue(self._call() is "foo@bar.baz")

    @test_util.patch_get_utility("certbot.display.ops.z_util")
    def test_ok_not_safe(self, mock_get_utility):
        mock_input = mock_get_utility().input
        mock_input.return_value = (display_util.OK, "foo@bar.baz")
        with mock.patch("certbot.display.ops.util.safe_email") as mock_safe_email:
            mock_safe_email.side_effect = [False, True]
            self.assertTrue(self._call() is "foo@bar.baz")

    @test_util.patch_get_utility("certbot.display.ops.z_util")
    def test_invalid_flag(self, mock_get_utility):
        invalid_txt = "There seem to be problems"
        mock_input = mock_get_utility().input
        mock_input.return_value = (display_util.OK, "foo@bar.baz")
        with mock.patch("certbot.display.ops.util.safe_email") as mock_safe_email:
            mock_safe_email.return_value = True
            self._call()
            self.assertTrue(invalid_txt not in mock_input.call_args[0][0])
            self._call(invalid=True)
            self.assertTrue(invalid_txt in mock_input.call_args[0][0])

    @test_util.patch_get_utility("certbot.display.ops.z_util")
    def test_optional_flag(self, mock_get_utility):
        mock_input = mock_get_utility().input
        mock_input.return_value = (display_util.OK, "foo@bar.baz")
        with mock.patch("certbot.display.ops.util.safe_email") as mock_safe_email:
            mock_safe_email.side_effect = [False, True]
            self._call(optional=False)
            for call in mock_input.call_args_list:
                self.assertTrue(
                    "--register-unsafely-without-email" not in call[0][0])

    @test_util.patch_get_utility("certbot.display.ops.z_util")
    def test_optional_invalid_unsafe(self, mock_get_utility):
        invalid_txt = "There seem to be problems"
        mock_input = mock_get_utility().input
        mock_input.return_value = (display_util.OK, "foo@bar.baz")
        with mock.patch("certbot.display.ops.util.safe_email") as mock_safe_email:
            mock_safe_email.side_effect = [False, True]
            self._call(invalid=True)
            self.assertTrue(invalid_txt in mock_input.call_args[0][0])


class ChooseAccountTest(unittest.TestCase):
    """Tests for certbot.display.ops.choose_account."""
    def setUp(self):
        zope.component.provideUtility(display_util.FileDisplay(sys.stdout,
                                                               False))

        self.accounts_dir = tempfile.mkdtemp("accounts")
        self.account_keys_dir = os.path.join(self.accounts_dir, "keys")
        os.makedirs(self.account_keys_dir, 0o700)

        self.config = mock.MagicMock(
            accounts_dir=self.accounts_dir,
            account_keys_dir=self.account_keys_dir,
            server="certbot-demo.org")
        self.key = KEY

        self.acc1 = account.Account(messages.RegistrationResource(
            uri=None, new_authzr_uri=None, body=messages.Registration.from_data(
                email="email1@g.com")), self.key)
        self.acc2 = account.Account(messages.RegistrationResource(
            uri=None, new_authzr_uri=None, body=messages.Registration.from_data(
                email="email2@g.com", phone="phone")), self.key)

    @classmethod
    def _call(cls, accounts):
        from certbot.display import ops
        return ops.choose_account(accounts)

    @test_util.patch_get_utility("certbot.display.ops.z_util")
    def test_one(self, mock_util):
        mock_util().menu.return_value = (display_util.OK, 0)
        self.assertEqual(self._call([self.acc1]), self.acc1)

    @test_util.patch_get_utility("certbot.display.ops.z_util")
    def test_two(self, mock_util):
        mock_util().menu.return_value = (display_util.OK, 1)
        self.assertEqual(self._call([self.acc1, self.acc2]), self.acc2)

    @test_util.patch_get_utility("certbot.display.ops.z_util")
    def test_cancel(self, mock_util):
        mock_util().menu.return_value = (display_util.CANCEL, 1)
        self.assertTrue(self._call([self.acc1, self.acc2]) is None)


class GenSSLLabURLs(unittest.TestCase):
    """Loose test of _gen_ssl_lab_urls. URL can change easily in the future."""
    def setUp(self):
        zope.component.provideUtility(display_util.FileDisplay(sys.stdout,
                                                               False))

    @classmethod
    def _call(cls, domains):
        from certbot.display.ops import _gen_ssl_lab_urls
        return _gen_ssl_lab_urls(domains)

    def test_zero(self):
        self.assertEqual(self._call([]), [])

    def test_two(self):
        urls = self._call(["eff.org", "umich.edu"])
        self.assertTrue("eff.org" in urls[0])
        self.assertTrue("umich.edu" in urls[1])


class GenHttpsNamesTest(unittest.TestCase):
    """Test _gen_https_names."""
    def setUp(self):
        zope.component.provideUtility(display_util.FileDisplay(sys.stdout,
                                                               False))

    @classmethod
    def _call(cls, domains):
        from certbot.display.ops import _gen_https_names
        return _gen_https_names(domains)

    def test_zero(self):
        self.assertEqual(self._call([]), "")

    def test_one(self):
        doms = [
            "example.com",
            "asllkjsadfljasdf.c",
        ]
        for dom in doms:
            self.assertEqual(self._call([dom]), "https://%s" % dom)

    def test_two(self):
        domains_list = [
            ["foo.bar.org", "bar.org"],
            ["paypal.google.facebook.live.com", "*.zombo.example.com"],
        ]
        for doms in domains_list:
            self.assertEqual(
                self._call(doms),
                "https://{dom[0]} and https://{dom[1]}".format(dom=doms))

    def test_three(self):
        doms = ["a.org", "b.org", "c.org"]
        # We use an oxford comma
        self.assertEqual(
            self._call(doms),
            "https://{dom[0]}, https://{dom[1]}, and https://{dom[2]}".format(
                dom=doms))

    def test_four(self):
        doms = ["a.org", "b.org", "c.org", "d.org"]
        exp = ("https://{dom[0]}, https://{dom[1]}, https://{dom[2]}, "
               "and https://{dom[3]}".format(dom=doms))

        self.assertEqual(self._call(doms), exp)


class ChooseNamesTest(unittest.TestCase):
    """Test choose names."""
    def setUp(self):
        zope.component.provideUtility(display_util.FileDisplay(sys.stdout,
                                                               False))
        self.mock_install = mock.MagicMock()

    @classmethod
    def _call(cls, installer):
        from certbot.display.ops import choose_names
        return choose_names(installer)

    @mock.patch("certbot.display.ops._choose_names_manually")
    def test_no_installer(self, mock_manual):
        self._call(None)
        self.assertEqual(mock_manual.call_count, 1)

    @test_util.patch_get_utility("certbot.display.ops.z_util")
    def test_no_installer_cancel(self, mock_util):
        mock_util().input.return_value = (display_util.CANCEL, [])
        self.assertEqual(self._call(None), [])

    @test_util.patch_get_utility("certbot.display.ops.z_util")
    def test_no_names_choose(self, mock_util):
        self.mock_install().get_all_names.return_value = set()
        domain = "example.com"
        mock_util().input.return_value = (display_util.OK, domain)

        actual_doms = self._call(self.mock_install)
        self.assertEqual(mock_util().input.call_count, 1)
        self.assertEqual(actual_doms, [domain])
        self.assertTrue(
            "configuration files" in mock_util().input.call_args[0][0])

    def test_sort_names_trivial(self):
        from certbot.display.ops import _sort_names

        #sort an empty list
        self.assertEqual(_sort_names([]), [])

        #sort simple domains
        some_domains = ["ex.com", "zx.com", "ax.com"]
        self.assertEqual(_sort_names(some_domains), ["ax.com", "ex.com", "zx.com"])

        #Sort subdomains of a single domain
        domain = ".ex.com"
        unsorted_short = ["e", "a", "z", "y"]
        unsorted_long = [us + domain for us in unsorted_short]

        sorted_short = sorted(unsorted_short)
        sorted_long = [us + domain for us in sorted_short]

        self.assertEqual(_sort_names(unsorted_long), sorted_long)

    def test_sort_names_many(self):
        from certbot.display.ops import _sort_names

        unsorted_domains = [".cx.com", ".bx.com", ".ax.com", ".dx.com"]
        unsorted_short = ["www", "bnother.long.subdomain", "a", "a.long.subdomain", "z", "b"]
        #Of course sorted doesn't work here ;-)
        sorted_short = ["a", "b", "a.long.subdomain", "bnother.long.subdomain", "www", "z"]

        to_sort = []
        for short in unsorted_short:
            for domain in unsorted_domains:
                to_sort.append(short+domain)
        sortd = []
        for domain in sorted(unsorted_domains):
            for short in sorted_short:
                sortd.append(short+domain)
        self.assertEqual(_sort_names(to_sort), sortd)


    @test_util.patch_get_utility("certbot.display.ops.z_util")
    def test_filter_names_valid_return(self, mock_util):
        self.mock_install.get_all_names.return_value = set(["example.com"])
        mock_util().checklist.return_value = (display_util.OK, ["example.com"])

        names = self._call(self.mock_install)
        self.assertEqual(names, ["example.com"])
        self.assertEqual(mock_util().checklist.call_count, 1)

    @test_util.patch_get_utility("certbot.display.ops.z_util")
    def test_filter_names_nothing_selected(self, mock_util):
        self.mock_install.get_all_names.return_value = set(["example.com"])
        mock_util().checklist.return_value = (display_util.OK, [])

        self.assertEqual(self._call(self.mock_install), [])

    @test_util.patch_get_utility("certbot.display.ops.z_util")
    def test_filter_names_cancel(self, mock_util):
        self.mock_install.get_all_names.return_value = set(["example.com"])
        mock_util().checklist.return_value = (
            display_util.CANCEL, ["example.com"])

        self.assertEqual(self._call(self.mock_install), [])

    def test_get_valid_domains(self):
        from certbot.display.ops import get_valid_domains
        all_valid = ["example.com", "second.example.com",
                     "also.example.com", "under_score.example.com",
                     "justtld"]
        all_invalid = ["öóòps.net", "*.wildcard.com", "uniçodé.com"]
        two_valid = ["example.com", "úniçøde.com", "also.example.com"]
        self.assertEqual(get_valid_domains(all_valid), all_valid)
        self.assertEqual(get_valid_domains(all_invalid), [])
        self.assertEqual(len(get_valid_domains(two_valid)), 2)

    @test_util.patch_get_utility("certbot.display.ops.z_util")
    def test_choose_manually(self, mock_util):
        from certbot.display.ops import _choose_names_manually
        # No retry
        mock_util().yesno.return_value = False
        # IDN and no retry
        mock_util().input.return_value = (display_util.OK,
                                          "uniçodé.com")
        self.assertEqual(_choose_names_manually(), [])
        # IDN exception with previous mocks
        with mock.patch(
                "certbot.display.ops.display_util.separate_list_input"
        ) as mock_sli:
            unicode_error = UnicodeEncodeError('mock', u'', 0, 1, 'mock')
            mock_sli.side_effect = unicode_error
            self.assertEqual(_choose_names_manually(), [])
        # Valid domains
        mock_util().input.return_value = (display_util.OK,
                                          ("example.com,"
                                           "under_score.example.com,"
                                           "justtld,"
                                           "valid.example.com"))
        self.assertEqual(_choose_names_manually(),
                         ["example.com", "under_score.example.com",
                          "justtld", "valid.example.com"])
        # Three iterations
        mock_util().input.return_value = (display_util.OK,
                                          "uniçodé.com")
        yn = mock.MagicMock()
        yn.side_effect = [True, True, False]
        mock_util().yesno = yn
        _choose_names_manually()
        self.assertEqual(mock_util().yesno.call_count, 3)


class SuccessInstallationTest(unittest.TestCase):
    # pylint: disable=too-few-public-methods
    """Test the success installation message."""
    @classmethod
    def _call(cls, names):
        from certbot.display.ops import success_installation
        success_installation(names)

    @test_util.patch_get_utility("certbot.display.ops.z_util")
    def test_success_installation(self, mock_util):
        mock_util().notification.return_value = None
        names = ["example.com", "abc.com"]

        self._call(names)

        self.assertEqual(mock_util().notification.call_count, 1)
        arg = mock_util().notification.call_args_list[0][0][0]

        for name in names:
            self.assertTrue(name in arg)


class SuccessRenewalTest(unittest.TestCase):
    # pylint: disable=too-few-public-methods
    """Test the success renewal message."""
    @classmethod
    def _call(cls, names):
        from certbot.display.ops import success_renewal
        success_renewal(names)

    @test_util.patch_get_utility("certbot.display.ops.z_util")
    def test_success_renewal(self, mock_util):
        mock_util().notification.return_value = None
        names = ["example.com", "abc.com"]

        self._call(names)

        self.assertEqual(mock_util().notification.call_count, 1)
        arg = mock_util().notification.call_args_list[0][0][0]

        for name in names:
            self.assertTrue(name in arg)

class SuccessRevocationTest(unittest.TestCase):
    # pylint: disable=too-few-public-methods
    """Test the success revocation message."""
    @classmethod
    def _call(cls, path):
        from certbot.display.ops import success_revocation
        success_revocation(path)

    @test_util.patch_get_utility("certbot.display.ops.z_util")
    def test_success_revocation(self, mock_util):
        mock_util().notification.return_value = None
        path = "/path/to/cert.pem"
        self._call(path)
        mock_util().notification.assert_called_once_with(
            "Congratulations! You have successfully revoked the certificate "
            "that was located at {0}{1}{1}".format(
                path,
                os.linesep), pause=False)
        self.assertTrue(path in mock_util().notification.call_args[0][0])

if __name__ == "__main__":
    unittest.main()  # pragma: no cover