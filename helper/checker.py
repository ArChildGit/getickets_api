def validate_price(price):
    """Memeriksa apakah harga valid sebagai integer."""
    try:
        return int(price)
    except ValueError:
        return None

def validate_password_strength(password):
    """
    Checks if the password is strong enough based on length.

    :param password: The password string to validate
    :return: "Weak" if < 6 characters, "Medium" if 6-10, "Strong" if > 10
    """
    if len(password) < 6:
        return "Weak"
    elif 6 <= len(password) <= 10:
        return "Medium"
    else:
        return "Strong"
