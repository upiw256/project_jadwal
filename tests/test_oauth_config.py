import unittest

from src.oauth_config import normalize_redirect_uri


class NormalizeRedirectUriTests(unittest.TestCase):
    def test_adds_trailing_slash_for_https_domain(self):
        self.assertEqual(
            normalize_redirect_uri("https://jadwal.sman1margaasih.sch.id"),
            "https://jadwal.sman1margaasih.sch.id/",
        )

    def test_preserves_existing_trailing_slash(self):
        self.assertEqual(
            normalize_redirect_uri("https://jadwal.sman1margaasih.sch.id/"),
            "https://jadwal.sman1margaasih.sch.id/",
        )


if __name__ == "__main__":
    unittest.main()
