from monetae.api.schemas.auth import ActionResult, StrictModel


class Page[ItemT](StrictModel):
    items: list[ItemT]
    next_cursor: str | None


class ArchiveRequest(StrictModel):
    reason: str | None = None


__all__ = ["ActionResult", "ArchiveRequest", "Page"]
