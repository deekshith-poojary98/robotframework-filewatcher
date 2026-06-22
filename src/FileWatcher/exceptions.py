class FileWatcherError(Exception):
    """Base exception for all FileWatcher library errors."""
    pass


class FileWatcherTimeoutError(FileWatcherError):
    """Raised when a wait operation times out waiting for a file system event."""
    pass


class DirectoryNotWatchedError(FileWatcherError):
    """Raised when trying to perform an action on a directory that is not currently being watched."""
    pass


class DirectoryAlreadyWatchedError(FileWatcherError):
    """Raised when trying to watch a directory that is already registered and watched."""
    pass
