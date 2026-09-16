import unittest

from meshtastic_builder.security import generate_public_token, validate_public_token


class SecurityTests(unittest.TestCase):
    def test_public_token_is_valid_and_not_short(self):
        token = generate_public_token()
        self.assertGreaterEqual(len(token), 32)
        self.assertEqual(validate_public_token(token), token)


if __name__ == "__main__":
    unittest.main()

