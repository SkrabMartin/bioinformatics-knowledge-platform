class ApplicationError(Exception):
    status_code = 400
    code = "application_error"

    def __init__(self, message: str, *, details: object | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class NotFoundError(ApplicationError):
    status_code = 404
    code = "not_found"


class ConflictError(ApplicationError):
    status_code = 409
    code = "conflict"


class InvalidInputError(ApplicationError):
    status_code = 422
    code = "validation_error"
