"""Project-wide constants. The only place where magic numbers are allowed to live."""

GRADE_MIN = 0.0
GRADE_MAX = 100.0
EXCELLENT_THRESHOLD = 90.0

# ФЕП-31с, ПМ-22, KN-31a: 2-5 capital letters, dash, two digits, optional lowercase suffix
GROUP_PATTERN = r"[А-ЯІЇЄҐA-Z]{2,5}-\d{2}[а-яіїєґa-z]?"
