class UnsupportedFileTypeError(Exception):
    """Raised when file type is not supported"""
    pass


class OsException(Exception):
    """Raised when OS-level operations fail"""
    pass


class ResourceNotFoundError(Exception):
    """Raised when a resource is not found"""
    pass


class TranscodingError(Exception):
    """Raised when transcoding operation fails"""
    pass


class StorageError(Exception):
    """Raised when storage operations fail"""
    pass