import re


async def sanitize_query(query):
    # Remove non-alphanumeric characters and spaces
    sanitized_query = re.sub(r'\W+', ' ', query)
    # Trim leading and trailing spaces
    sanitized_query = sanitized_query.strip()
    return sanitized_query
