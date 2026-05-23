import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from restaurant_agent.utils import normalize_phone, is_valid_phone

test_cases = [
    ("(+92) 300 1234567", "+923001234567", True),
    ("0300 1234567", "03001234567", True),
    ("123", "123", False),
    ("+1-555-123-4567", "+15551234567", True),
    ("   (555) 123-4567   ", "5551234567", True),
]

print("Running phone normalization tests...")
for input_str, expected, should_be_valid in test_cases:
    normalized = normalize_phone(input_str)
    valid = is_valid_phone(input_str)
    print(f"Input: {input_str:20} -> Normalized: {normalized:15} | Valid: {valid}")
    assert normalized == expected
    assert valid == should_be_valid

print("\nAll tests passed!")
