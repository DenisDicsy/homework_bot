import logging
import os
import sys
import time

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (
    ApiRequestException,
    HomeWorkApiException,
    InvalidTelegramTokenException,
    NoneEnvVariableException,
    NotOkStatusCodeException,
)

load_dotenv()


PRACTICUM_TOKEN = os.getenv("PRACTICUM_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

RETRY_PERIOD = 600
ENDPOINT = "https://practicum.yandex.ru/api/user_api/homework_statuses/"
HEADERS = {"Authorization": f"OAuth {PRACTICUM_TOKEN}"}


HOMEWORK_VERDICTS = {
    "approved": "Работа проверена: ревьюеру всё понравилось. Ура!",
    "reviewing": "Работа взята на проверку ревьюером.",
    "rejected": "Работа проверена: у ревьюера есть замечания.",
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(
    logging.Formatter(
        "%(asctime)s  [%(levelname)s] %(funcName)s(%(lineno)d)  %(message)s"
    )
)
logger.addHandler(handler)


def check_tokens():
    """
    Функция проверки того, что определены все переменные окружения.

    Выбрысывает ошибка и логируется уровнем critical в противном случае.
    """
    env_variables = {
        PRACTICUM_TOKEN: "PRACTICUM_TOKEN",
        TELEGRAM_TOKEN: "TELEGRAM_TOKEN",
        TELEGRAM_CHAT_ID: "TELEGRAM_CHAT_ID",
    }
    for env_variable in env_variables:
        if not env_variable:
            logger.critical(
                f"Нет переменной окружения {env_variables.get(env_variable)}"
            )
            return False
    return True


def send_message(bot: telegram.Bot, message):
    """
    Отправляет сообщение message через telegram Bot - bot.

    При неудачное отправке логируем ошибку уровнем error
    """
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug("Отправили сообщение через бота")
    except Exception as error:
        logger.error(f"Не удалось отправить сообщение через бота{error}")


def get_api_answer(timestamp):
    """
    Делаем запрос к API Практикума.

    При неудачном запросе выбрасываем исключение
    Проверяем что статус ответа ОК.

    Возвращаем ответ API, приведенный к Python словарю
    """
    try:
        response = requests.get(
            url=ENDPOINT, headers=HEADERS, params={"from_date": timestamp}
        )
        logger.debug("Получили ответ от API Практикума")
    except requests.RequestException as error:
        logger.error(f"Получили ошибку при запросе {error}")
        raise ApiRequestException("Ошибка при запросе")
    if response.status_code != requests.codes.ok:
        logger.error("Мы получили плохой ответ")
        raise NotOkStatusCodeException("Мы получили плохой ответ")
    return response.json()


def check_response(response):
    """
    Проверяет то, что ответ API был приведен к типу данных dict.
    а так же то, что в ответе имеется ключ homeworks типа данных list
    """
    if not isinstance(response, dict):
        raise TypeError("Response должен быть типом данных dict")
    if "homeworks" not in response or "current_date" not in response:
        raise TypeError("Неправильное наполнение ответа API")
    if not isinstance(response.get("homeworks"), list):
        raise TypeError("Значение homework должно быть типом данных list")
    return True


def parse_status(homework):
    """
    Получаем статус самой свежей проверки ДЗ.

    Проверяем что в ответе API есть имя и статус ДЗ.
    """
    homework_name = homework.get("homework_name", None)
    homework_status = homework.get("status", None)
    if homework_name is None or homework_status not in HOMEWORK_VERDICTS:
        raise HomeWorkApiException(
            "Неправильное наполнение словаря с результатами ДЗ"
        )
    verdict = HOMEWORK_VERDICTS.get(homework_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        raise NoneEnvVariableException("Нет переменной окружения")
    try:
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
    except telegram.error.InvalidToken:
        raise InvalidTelegramTokenException("Некорректный token для бота")
    logger.debug("Запуск бота")
    timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            homework_list = response.get("homeworks")
            if homework_list:
                send_message(bot, parse_status(homework_list[0]))
            else:
                logger.debug("Новых обновлений по ДЗ нет.")
            timestamp = response.get("current_date")

        except TypeError as error:
            logger.critical(f"Некорректный response. Ошибка - {error}")
            sys.exit(f"Некорретный respose. Ошибка - {error}")

        except Exception as error:
            logger.error(f"Сбой в работе программы: {error}")
            message = f"Сбой в работе программы: {error}"
            send_message(bot, message)

        finally:
            logger.debug("Засыпаем на 10 минут")
            time.sleep(RETRY_PERIOD)


if __name__ == "__main__":
    main()
