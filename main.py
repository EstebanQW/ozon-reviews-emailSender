import random
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests

# ==========================================================#
COMPANY_ID = "123456"  # id компании, можно посмотреть на странице компании (например https://www.ozon.ru/seller/ooo-mebelnaya-fabrika-volzhanka-1234/products/?miniapp=seller_1234 - id компании 1234)
FROM_ADDR = "example1@mail.ru"  # почта, с которой будет уходить письмо
MAIL_PASSWORD = "password"  # пароль от почты для внешних приложений. Для mail.ru брать по ссылке - https://account.mail.ru/user/2-step-auth/passwords
TO_ADDR = "example2@mail.ru"  # почта, на которую отправлять письмо
REVIEW_SUM = 10  # количество кейсов, которые необходимо отправить (1 кейс = 10 отзывов)
COOKIE = "cookie"  # куки
# ==========================================================#


# Получает отзывы с платформы Ozon через API
def get_rate(value_cases: int, cookie: str) -> list:
    url = "https://seller.ozon.ru/api/v3/review/list"
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "ru",
        "content-type": "application/json",
        "priority": "u=1, i",
        "sec-ch-ua": '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "x-o3-app-name": "seller-ui",
        "x-o3-company-id": COMPANY_ID,
        "x-o3-language": "ru",
        "x-o3-page-type": "review",
        "cookie": cookie,
        "Referer": "https://seller.ozon.ru/app/reviews",
        "Referrer-Policy": "strict-origin-when-cross-origin",
    }

    last_id = None
    last_timestamp = None
    body = {
        "with_counters": False,
        "sort": {"sort_by": "PUBLISHED_AT", "sort_direction": "DESC"},
        "company_type": "seller",
        "filter": {"interaction_status": ["NOT_VIEWED"]},
        "company_id": COMPANY_ID,
        "pagination_last_timestamp": last_timestamp,
        "pagination_last_uuid": last_id,
    }
    all_cases = []  # список полученных отзывов
    max_retries = 10  # Количество повторных запросов

    for cases in range(value_cases):
        retries = 0  # Счетчик повторных запросов
        while retries <= max_retries:
            try:
                print(
                    f"Отправляю запрос на сервер OZON для получения отзывов. Запрос {cases+1} из {value_cases}."
                )
                response = requests.post(url, headers=headers, json=body)
                response.raise_for_status()
                print(last_id)
                print(last_timestamp)
                print()
                if response.status_code == 401:
                    print("Ошибка 401: Не авторизован")
                    return []  # Прервать выполнение функции
                data = response.json()
                for case in data["result"]:
                    all_cases.append(case)
                last_id = data["pagination_last_uuid"]
                last_timestamp = data["pagination_last_timestamp"]
                body["pagination_last_uuid"] = last_id
                body["pagination_last_timestamp"] = last_timestamp
                time.sleep(random.uniform(2, 4))
                break  # Выход из цикла, если запрос успешный

            except requests.exceptions.RequestException as err:
                print(f"Ошибка запроса: {err}")
                retries += 1
                if retries <= max_retries:
                    print("Повторный запрос через 30 секунд...")
                    time.sleep(30)
                else:
                    print(
                        "Все повторные запросы исчерпаны. Буду отправлять то, что успел получить."
                    )
                    return all_cases
            except Exception as err:
                print(f"Неизвестная ошибка: {err}")
                print("Повторный запрос через 30 секунд...")
                time.sleep(30)
                break
    return all_cases


# Отправляет отзывы на указанный email
def send_mail_ozon(value: int, cookie: str) -> None:
    cases = get_rate(value, cookie)
    if not cases:
        print(
            "Нет отзывов для отправки.\nОшибка 401: Не авторизован.\nПроверь корректность cookie."
        )
        return
    sent_cases = 0  # переменная для хранения количества отправленных кейсов
    for case in cases:
        # Тема для письма
        tema = case["uuid"]
        # Тело для письма
        body = f"""<p><b>Текст отзыва:</b> {case['text']['comment']} {case['text']['positive']} {case['text']['negative']}</p>
<br>
<p><b>Ссылка на товар OZON:</b> <a href="firefox:{case['product']['url']}">{case['product']['url']}</a></p>
<br>
<p>Оценка клиента: {case['rating']}</p>
<p>Статус заказа: {case['orderDeliveryType']}</p>
<p>Название бренда: {case['product']['brand_info']['name']}</p>
<p>ID отзыва: {case['id']}</p>
<p>Дата поступления отзыва: {case['published_at']}</p>
<p>Артикул на OZON: {case['sku']}</p>
<p>Артикул наш сайт: {case['product']['offer_id']}</p>
<p>Название товара: {case['product']['title']}</p>
"""
        print(f"Начинаю отправку сообщения(кейса) на email {TO_ADDR}.")

        msg = MIMEMultipart()
        msg["From"] = FROM_ADDR
        msg["To"] = TO_ADDR
        msg["Subject"] = tema
        msg.attach(MIMEText(body, "html"))

        max_retries = 2  # количество попыток отправки email
        case_sent = False  # флаг, указывающий, был ли кейс отправлен

        for _ in range(max_retries):
            try:
                server = smtplib.SMTP_SSL("smtp.mail.ru", 465)
                server.login(FROM_ADDR, MAIL_PASSWORD)
                text = msg.as_string()
                server.sendmail(FROM_ADDR, TO_ADDR, text)
                server.quit()
                case_sent = True
                current_index = cases.index(case)
                print(f"review id = {tema}")
                print(
                    f"Сообщение отправлено. Осталось отправить: {len(cases[current_index:])-1}шт."
                )
                print("_____________________________________________")
                print()
                time.sleep(random.uniform(1, 2))
                break
            except smtplib.SMTPException as e:
                print(f"Ошибка при отправке письма: {e}. Повторяю отправку...")
                retry_delay = 2  # задержка между попытками в секундах
                time.sleep(retry_delay)
        else:
            print("Все попытки отправки письма не увенчались успехом. Ошибка.")
        if case_sent:
            sent_cases += 1
        time.sleep(1)
    print("Все сообщения(кейсы) отправлены.")


if __name__ == "__main__":
    send_mail_ozon(REVIEW_SUM, COOKIE)
