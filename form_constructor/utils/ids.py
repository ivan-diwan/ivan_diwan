class IdGenerator:
    def __init__(self) -> None:
        self._counters: dict[str, int] = {}

    def next(self, prefix: str) -> str:
        current = self._counters.get(prefix, 0) + 1
        self._counters[prefix] = current
        return f"{prefix}_{current}"

    def reset(self) -> None:
        self._counters.clear()

    def seed_from_existing_ids(self, entity_ids: list[str]) -> None:
        for entity_id in entity_ids:
            prefix, separator, suffix = entity_id.rpartition("_")
            if not separator or not suffix.isdigit():
                continue
            current = int(suffix)
            previous = self._counters.get(prefix, 0)
            if current > previous:
                self._counters[prefix] = current
