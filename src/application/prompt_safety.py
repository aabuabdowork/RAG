import re

TAG_PATTERN = re.compile(r"</?\s*(context|question)\s*>", re.IGNORECASE)


def strip_tags(text: str) -> str:
    return TAG_PATTERN.sub("", text)
