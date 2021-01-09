class FilestorageError(RuntimeError):
    """Base class for all errors in this library"""

    pass


class FileNotAllowed(FilestorageError):
    """The provided file is not allowed."""

    pass


class FileExtensionNotAllowed(FilestorageError):
    """The provided file extension is not allowed."""

    pass


class FilestorageConfigError(FilestorageError):
    """Error in the configuration."""

    pass
