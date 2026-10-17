class BusinessError(Exception):
    """Erro de operação que pode ser apresentado ao usuário."""


class ConflictError(BusinessError):
    pass


class AuthorizationError(BusinessError):
    pass
