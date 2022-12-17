import os
import time
import requests
import telegram
import logging

from dotenv import load_dotenv

load_dotenv()


PRACTICUM_TOKEN = os.getenv("PRACTICUM_TOKEN", None)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", None)
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", None)

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
    logging.Formatter("%(asctime)s  [%(levelname)s]  %(message)s")
)
logger.addHandler(handler)


def check_tokens():
    """
    Функция проверки того, что определены все переменные окружения.

    Выбрысывает ошибка и логируется уровнем critical в противном случае.
    """
    if not all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        logger.critical("Не хватает переменных окружения")
        raise Exception("не хватает переменных окружения")


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
        raise Exception("Ошибка при запросе")
    if response.status_code != requests.codes.ok:
        logger.error("Мы получили плохой ответ")
        raise Exception("Мы получили плохой ответ")
    return response.json()


def check_response(response):
    """
    Проверяет то, что ответ API был приведен к типу данных dict.
    а так же то, что в ответе имеется ключ homeworks типа данных list
    """
    if not isinstance(response, dict) or not isinstance(
        response.get("homeworks"), list
    ):
        raise TypeError


def parse_status(homework):
    """
    Получаем статус самой свежей проверки ДЗ.

    Проверяем что в ответе API есть имя и статус ДЗ.
    """
    homework_name = homework.get("homework_name", None)
    homework_status = homework.get("status", None)
    verdict = HOMEWORK_VERDICTS.get(homework_status)
    if homework_name is None or homework_status not in HOMEWORK_VERDICTS:
        raise Exception("Неправильное наполнение словаря с результатами ДЗ")
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    logger.debug("Запуск бота")
    timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            homework_list = response.get("homeworks")
            if homework_list:
                send_message(bot, parse_status(homework_list[0]))
            timestamp = response.get("current_date")

        except Exception as error:
            message = f"Сбой в работе программы: {error}"
            send_message(bot, message)

        finally:
            logger.debug("Засыпаем на 10 минут")
            time.sleep(RETRY_PERIOD)


if __name__ == "__main__":
    main()
