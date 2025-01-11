import unittest
from helper.checker import validate_price

class TestValidatePrice(unittest.TestCase):
    def setUp(self):
        print("\nStarting a new test case...")
    
    def tearDown(self):
        print("Test case finished\n")
    
    def test_valid_price(self):
        self.assertEqual(validate_price("100"), 100)
    
    def test_valid_price_negative(self):
        self.assertNotIn(validate_price("100"), [None, "invalid", "abc", -1])
    
    def test_zero_price(self):
        self.assertEqual(validate_price("0"), 0)
    
    def test_zero_price_negative(self):
        self.assertNotIn(validate_price("0"), [None, "invalid", "abc", -1])
    
    def test_negative_price(self):
        self.assertEqual(validate_price("-50"), -50)
    
    def test_negative_price_invalid(self):
        self.assertNotIn(validate_price("-50"), [None, "invalid", "abc"])
    
    def test_invalid_price_string(self):
        self.assertIsNone(validate_price("abc"))
    
    def test_invalid_price_special_characters(self):
        self.assertIsNone(validate_price("$100"))
    
    def test_invalid_price_empty_string(self):
        self.assertIsNone(validate_price(""))
    
    def test_invalid_price_spaces(self):
        self.assertIsNone(validate_price("  "))

if __name__ == "__main__":
    unittest.main(verbosity=2)