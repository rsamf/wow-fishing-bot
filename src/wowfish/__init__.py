"""wowfish: a vision-based fishing bot for World of Warcraft: Forever."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("wowfish")
except PackageNotFoundError:  # running from a source tree without install
    __version__ = "0.0.0+unknown"
