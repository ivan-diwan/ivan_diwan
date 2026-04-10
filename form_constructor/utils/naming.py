def make_default_name(prefix: str, index: int) -> str:
    return f"{prefix}_{index}"


def make_unique_name(existing_names: set[str], prefix: str) -> str:
    index = 1
    while True:
        candidate = make_default_name(prefix, index)
        if candidate not in existing_names:
            return candidate
        index += 1
