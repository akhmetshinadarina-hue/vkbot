import time
import os
from datetime import datetime
from dotenv import load_dotenv
import vk_api
from vk_api.exceptions import ApiError

load_dotenv()

TOKEN = os.getenv('VK_TOKEN')
TARGET_USER_ID = os.getenv('TARGET_USER_ID')
YOUR_USER_IDS_RAW = os.getenv('YOUR_USER_IDS')

# Проверка обязательных переменных
if not TOKEN or not TARGET_USER_ID or not YOUR_USER_IDS_RAW:
    print("ОШИБКА: не все переменные заданы в файле .env")
    print(f"VK_TOKEN: {'задан' if TOKEN else 'ПУСТО'}")
    print(f"TARGET_USER_ID: {'задан' if TARGET_USER_ID else 'ПУСТО'}")
    print(f"YOUR_USER_IDS: {'задан' if YOUR_USER_IDS_RAW else 'ПУСТО'}")
    exit(1)

# Преобразуем строку "123,456" в список целых чисел
try:
    YOUR_USER_IDS = [int(uid.strip()) for uid in YOUR_USER_IDS_RAW.split(',') if uid.strip()]
except ValueError:
    print("ОШИБКА: YOUR_USER_IDS должен содержать числа через запятую, например: 832015946,433070885")
    exit(1)

if not YOUR_USER_IDS:
    print("ОШИБКА: список получателей пуст.")
    exit(1)

vk_session = vk_api.VkApi(token=TOKEN)
vk = vk_session.get_api()

# Как часто проверять статус (секунды)
CHECK_INTERVAL = 15

last_online_status = None


def log(message):
    now = datetime.now().strftime('%H:%M:%S')
    print(f"[{now}] {message}")


def check_online(user_id):
    try:
        response = vk.users.get(
            user_ids=user_id,
            fields='online,last_seen'
        )
        if response:
            user = response[0]
            is_online = user.get('online') == 1
            last_seen = user.get('last_seen', {})
            platform = last_seen.get('platform', '?')
            last_seen_time = last_seen.get('time', 0)
            if last_seen_time:
                last_seen_str = datetime.fromtimestamp(last_seen_time).strftime('%d.%m %H:%M')
            else:
                last_seen_str = 'скрыто'
            return is_online, platform, last_seen_str
    except ApiError as e:
        if e.code == 6:
            log("Flood control. Жду 60 секунд...")
            time.sleep(60)
        elif e.code == 5:
            log("ОШИБКА: токен недействителен. Создайте новый.")
            exit(1)
        elif e.code == 15:
            log("ОШИБКА: нет доступа. Проверьте права токена.")
            exit(1)
        else:
            log(f"Ошибка API: {e}")
    except Exception as e:
        log(f"Неизвестная ошибка: {e}")
    return None


def send_notification(message):
    """Отправляет сообщение всем получателям из списка."""
    success_count = 0
    fail_count = 0

    for uid in YOUR_USER_IDS:
        try:
            vk.messages.send(
                user_id=uid,
                message=message,
                random_id=int(time.time() * 1000) + uid
            )
            log(f"  → отправлено получателю {uid}")
            success_count += 1
            time.sleep(0.5)
        except ApiError as e:
            log(f"  → ошибка для {uid}: {e}")
            fail_count += 1
        except Exception as e:
            log(f"  → ошибка для {uid}: {e}")
            fail_count += 1

    log(f"Итог отправки: успешно {success_count}, ошибок {fail_count}")
    return success_count > 0


def main():
    global last_online_status

    log("=" * 50)
    log("Бот запущен. Отслеживаю статус.")
    log(f"Получатели уведомлений: {YOUR_USER_IDS}")
    log(f"Проверка статуса: каждые {CHECK_INTERVAL} сек.")
    log("=" * 50)

    while True:
        result = check_online(TARGET_USER_ID)

        if result is not None:
            is_online, platform, last_seen = result
            status_text = 'ОНЛАЙН' if is_online else 'офлайн'

            log(f"Статус: {status_text} | последний визит: {last_seen}")

            # Первая проверка — просто запоминаем, ничего не отправляем
            if last_online_status is None:
                last_online_status = is_online
                log("Первый запуск. Уведомление не отправляется.")

            # Статус изменился
            elif is_online != last_online_status:
                if is_online:
                    send_notification('Выложен новый пост "Цитаты.Мемы.Сохраненки"')
                else:
                    send_notification("Пост удален")
                last_online_status = is_online

        time.sleep(CHECK_INTERVAL)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        log("Бот остановлен пользователем.")
