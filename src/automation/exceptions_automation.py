class RegisterTelegramException(Exception):
    pass


class CannotRetrieveSMSCode(RegisterTelegramException):
    pass


class NoTelegramApiInfoFoundException(RegisterTelegramException):
    pass


class AddUserException(Exception):
    pass


class CannotOpenLoadPhoneNumbers(AddUserException):
    pass


class NoTelegramApiInfoFoundAddUserException(AddUserException):
    pass


class ClientNotAuthorizedException(AddUserException):
    pass


class PhoneNumberAndFileNameDifferentException(Exception):
    pass
