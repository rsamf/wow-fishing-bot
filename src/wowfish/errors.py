"""Exceptions shared across wowfish."""


class NotSupported(Exception):
    def __init__(self, detail: str) -> None:
        super().__init__(f"wowfish does not support {detail} yet.")
