import unittest
from helper.checker import validate_password_strength  # Sesuaikan path dengan proyek Anda

class TestValidatePasswordStrength(unittest.TestCase):
    def test_weak_password(self):
        self.assertEqual(validate_password_strength("abc"), "Weak")
        self.assertEqual(validate_password_strength("12345"), "Weak")

    def test_medium_password(self):
        self.assertEqual(validate_password_strength("abcdef"), "Medium")
        self.assertEqual(validate_password_strength("pass1234"), "Medium")

    def test_strong_password(self):
        self.assertEqual(validate_password_strength("verysecurepassword"), "Strong")
        self.assertEqual(validate_password_strength("P@ssw0rdLonger"), "Strong")

if __name__ == "__main__":
    unittest.main(verbosity=2)
