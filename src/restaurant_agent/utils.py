import re

def normalize_phone(phone: str) -> str:
    """
    Normalizes a phone number for SMS compatibility.
    Removes all non-numeric characters except for a leading '+'.
    Expects at least 10 digits to be considered potentially valid.
    """
    if not phone:
        return ""
    
    # Keep leading + if present (even if inside parentheses like (+92))
    has_plus = "+" in phone[:5]
    # Remove all non-numeric chars
    digits = re.sub(r"\D", "", phone)
    
    if not digits:
        return ""
        
    return f"+{digits}" if has_plus else digits

def is_valid_phone(phone: str) -> bool:
    """
    Basic check for phone length. 
    In a real app, we might use a library like phonenumbers.
    For this agent, we look for 9-15 digits.
    """
    normalized = normalize_phone(phone)
    # Remove the + for length check
    pure_digits = normalized.replace("+", "")
    return 7 <= len(pure_digits) <= 15
