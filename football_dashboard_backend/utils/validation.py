import re

# Allow either:
#  - SELECT … FROM …
#  - WITH … SELECT … FROM …
_SFW = re.compile(
    r"^\s*(?:with\b[\s\S]+?\bselect\b|select\b)[\s\S]+?\bfrom\b",
    re.IGNORECASE,
)

FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|create)\b",
    re.IGNORECASE,
)

def is_safe_sql(sql: str) -> bool:
    sql = sql.strip()
    # single trailing semicolon is fine if stripped earlier
    if ";" in sql:
        return False
    if FORBIDDEN.search(sql):
        return False
    return bool(_SFW.match(sql))
