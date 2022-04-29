class RegisterTelegramException(Exception):
    pass


class CannotRetrieveSMSCode(RegisterTelegramException):
    pass


class NoTelegramApiInfoFoundException(RegisterTelegramException):
    pass
