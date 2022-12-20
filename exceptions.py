class NoneEnvVariableException(Exception):
    '''
    Ошибка незаполненной переменной окружения.
    '''
    pass


class ApiRequestException(Exception):
    '''
    Ошибка при обращении к API.
    '''
    pass


class NotOkStatusCodeException(Exception):
    '''
    Ошибка статус код не 2хх.
    '''
    pass


class HomeWorkApiException(Exception):
    '''
    Ошибка при неправильном наполнении словаря homework в ответе API.
    '''
    pass


class InvalidTelegramTokenException(Exception):
    '''
    Ошибка при некорректном токене для бота Telegram
    '''
    pass