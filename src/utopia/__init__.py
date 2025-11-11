# read version from installed package
from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("utopia-pkg")  # match your project name in pyproject.toml
except PackageNotFoundError:
    __version__ = "unknown"