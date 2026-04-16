from fastapi import HTTPException, status


class NotifyError(HTTPException):
    """Base class for exceptions in this module."""


class NotFoundError(NotifyError):
    def __init__(self, resource: str, identifier: str | int) -> None:
        self.resource = resource
        self.identifier = identifier
        super().__init__(f"{resource} '{identifier}' not found")


class ConflictError(NotifyError):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class PermissionError(NotifyError):
    def __init__(self, message: str = "Permission denied") -> None:
        super().__init__(message)


# HTTP exception factories


def http_404(resource: str, identifier: str | int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail=f"Resource '{resource}' not found"
    )


def http_409(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def http_403(detail: str = "Permission denied") -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
