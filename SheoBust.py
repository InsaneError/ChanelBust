from telethon import events, Button
from telethon.tl.functions.contacts import BlockRequest, UnblockRequest
from telethon.tl.types import User
from .. import loader, utils
import asyncio
import time
from datetime import datetime


@loader.tds
class SubCheckBot(loader.Module):
    """Буст канала от @sheomod"""

    strings = {
        'name': 'SubChecker',
        'not_subscribed': "<b>Вы не подписаны на наш канал!</b>\nПожалуйста, подпишитесь на канал {channel_link}, чтобы продолжить общение.\n\n<b>В течении минуты вас разблокируют.</b>",
        'subscribed': "<b>Спасибо за подписку! Вы были разблокированы.</b>",
        'channel_not_set': "<b>Канал для проверки подписки не настроен!</b>\n\nИспользуйте команду .subchannel [юзернейм или ссылка] для настройки канала.\nПример: .subchannel @my_channel",
        'channel_set': "<b>Канал для проверки подписки установлен:</b> {}",
        'current_channel': "<b>Текущий канал для проверки:</b> {}\n\n<b>ID канала:</b> <code>{}</code>",
        'invalid_channel': "<b>Не удалось найти канал!</b>\n\nПроверьте правильность юзернейма или ссылки и убедитесь, что бот имеет доступ к каналу.",
        'test_success': "<b>Тест пройден успешно!</b>\n\nБот может получить информацию о канале и его участниках.",
        'test_failed': "<b>Тест не пройден!</b>\n\nОшибка: {}",
        'no_permission': "<b>Нет прав доступа!</b>\n\nУбедитесь, что бот является администратором канала или имеет права на просмотр участников.",
        'bot_detected': "<b>Бот обнаружен!</b>\n\nБоты не проходят проверку подписки.",
        'custom_message_set': "<b>Кастомное сообщение установлено!</b>",
        'custom_message_cleared': "<b>Кастомное сообщение сброшено!</b>",
        'current_custom_message': "<b>Текущее кастомное сообщение:</b>\n\n{}",
        'no_custom_message': "<b>Кастомное сообщение не установлено.</b>\nИспользуется стандартное сообщение.",
        'whitelist_added': "<b>Пользователь добавлен в белый список!</b>\n\nID: <code>{}</code>",
        'whitelist_removed': "<b>Пользователь удален из белого списка!</b>\n\nID: <code>{}</code>",
        'whitelist_not_found': "<b>Пользователь не найден в белом списке!</b>",
        'whitelist_empty': "<b>Белый список пуст!</b>",
        'whitelist_cleared': "<b>Белый список очищен!</b>\n\nУдалено пользователей: {}",
        'whitelist_list': "<b>Белый список пользователей:</b>\n\n{}",
        'user_in_whitelist': "<b>Пользователь в белом списке</b>\n\nID: <code>{}</code>\nДобавлен: {}",
        'user_not_in_whitelist': "<b>Пользователь не в белом списке!</b>",
        'invalid_user_id': "<b>Неверный ID пользователя!</b>\nID должен быть числом.",
        'no_reply': "<b>Ответьте на сообщение пользователя или укажите ID!</b>",
        'check_interval_set': "<b>Интервал проверки установлен:</b> {} секунд\n\nМинимальное значение: 30 секунд",
        'current_check_interval': "<b>Текущий интервал проверки:</b> {} секунд",
        'invalid_interval': "<b>Неверный интервал!</b>\n\nУкажите число секунд (минимум 30).",
        'user_blocked': "<b>Пользователь заблокирован!</b>\n\nID: <code>{}</code>\nПричина: не подписан на канал",
        'user_unblocked': "<b>Пользователь разблокирован!</b>\n\nID: <code>{}</code>\nПричина: подписался на канал",
        'blocked_users': "<b>Заблокированные пользователи:</b>\n\n{}",
        'no_blocked_users': "<b>Нет заблокированных пользователей!</b>",
        'blocked_user_info': "<b>Информация о блокировке:</b>\n\nID: <code>{}</code>\nЗаблокирован: {}\nПроверок: {}\nПоследняя проверка: {}",
        'checking_subscriptions': "<b>Запущена фоновая проверка подписок...</b>\n\nПроверяем {} пользователей",
        'check_complete': "<b>Проверка завершена!</b>\n\nПроверено: {}\nРазблокировано: {}\nВсе еще не подписаны: {}",
        'force_check_started': "<b>Принудительная проверка запущена!</b>\n\nПроверяем {} пользователей...",
        'already_blocked': "<b>Пользователь уже заблокирован!</b>",
        'already_unblocked': "<b>Пользователь уже разблокирован!</b>",
        'block_failed': "<b>Не удалось заблокировать пользователя!</b>\n\nОшибка: {}",
        'unblock_failed': "<b>Не удалось разблокировать пользователя!</b>\n\nОшибка: {}",
        'flood_wait': "<b>Превышен лимит запросов!</b>\n\nПожалуйста, подождите {} секунд перед следующей операцией."
    }

    def __init__(self):
        self.check_task = None
        self.check_running = False
        self.last_operation_time = {}  # Для контроля флуда

    async def client_ready(self, client, db):
        self.client = client
        self.db = db

        # Загрузка настроек канала
        self.channel_username = self.db.get("SubChecker", "channel_username", "")
        self.channel_link = self.db.get("SubChecker", "channel_link", "")
        self.channel_id = self.db.get("SubChecker", "channel_id", None)

        # Загрузка сообщений о неподписке
        self.not_subscribed_msgs = self.db.get("SubChecker", "not_subscribed_msgs", {})

        # Загрузка кастомного сообщения
        self.custom_message = self.db.get("SubChecker", "custom_message", "")

        # Загрузка белого списка
        self.whitelist = self.db.get("SubChecker", "whitelist", {})

        # Загрузка заблокированных пользователей
        self.blocked_users = self.db.get("SubChecker", "blocked_users", {})

        # Интервал проверки (по умолчанию 60 секунд)
        self.check_interval = self.db.get("SubChecker", "check_interval", 60)
        if self.check_interval < 30:
            self.check_interval = 30

        # Включение/выключение модуля
        self.enabled = self.db.get("SubChecker", "enabled", True)

        # Запуск фоновой проверки
        if self.enabled and self.channel_id and not self.check_running:
            await self.start_background_checker()

    async def start_background_checker(self):
        """Запуск фоновой проверки"""
        if self.check_task and not self.check_task.done():
            return

        self.check_running = True
        self.check_task = asyncio.create_task(self.background_checker())

    async def stop_background_checker(self):
        """Остановка фоновой проверки"""
        self.check_running = False
        if self.check_task and not self.check_task.done():
            self.check_task.cancel()
            try:
                await self.check_task
            except asyncio.CancelledError:
                pass
        self.check_task = None

    async def background_checker(self):
        """Фоновая проверка подписок заблокированных пользователей"""
        while self.check_running:
            try:
                if not self.enabled or not self.channel_id:
                    await asyncio.sleep(60)
                    continue

                # Получаем участников канала (только последние 20 для оптимизации)
                try:
                    participant_ids = await self.get_channel_participants()
                except Exception as e:
                    print(f"Ошибка получения участников канала: {e}")
                    await asyncio.sleep(self.check_interval)
                    continue

                # Проверяем каждого заблокированного пользователя
                for user_id_str, data in list(self.blocked_users.items()):
                    if not self.check_running:
                        break

                    user_id = int(user_id_str)

                    # Пропускаем если пользователь в белом списке
                    if self.is_whitelisted(user_id):
                        if user_id_str in self.blocked_users:
                            await self.unblock_user(user_id, "пользователь в белом списке")
                        continue

                    # Проверяем подписку
                    if user_id in participant_ids:
                        # Пользователь подписался - разблокируем
                        await self.unblock_user(user_id, "подписался на канал")
                    else:
                        # Обновляем счетчик проверок
                        self.blocked_users[user_id_str]['check_count'] = self.blocked_users[user_id_str].get(
                            'check_count', 0) + 1
                        self.blocked_users[user_id_str]['last_check'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        self.db.set("SubChecker", "blocked_users", self.blocked_users)

                # Ждем перед следующей проверкой
                await asyncio.sleep(self.check_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Ошибка в фоновой проверке: {e}")
                await asyncio.sleep(60)

    async def get_channel_participants(self):
        """Получить ID участников канала (оптимизированная версия)"""
        if not self.channel_id:
            return set()

        participant_ids = set()
        try:
            # Получаем только последние 20 участников для оптимизации
            participants = await self.client.get_participants(self.channel_id, limit=20)
            participant_ids = {p.id for p in participants}
        except Exception as e:
            print(f"Ошибка при получении участников: {e}")

        return participant_ids

    def check_flood_limit(self, user_id):
        """Проверка ограничения на частоту операций"""
        current_time = time.time()
        if user_id in self.last_operation_time:
            time_diff = current_time - self.last_operation_time[user_id]
            if time_diff < 2:  # Минимум 2 секунды между операциями
                return True
        self.last_operation_time[user_id] = current_time
        return False

    async def block_user(self, user_id):
        """Блокировка пользователя с обработкой ошибок"""
        # Проверка на флуд
        if self.check_flood_limit(user_id):
            raise Exception("Слишком частые операции. Подождите 2 секунды.")

        # Проверка, не заблокирован ли уже
        if str(user_id) in self.blocked_users:
            return True  # Уже заблокирован

        try:
            await self.client(BlockRequest(id=user_id))

            # Сохраняем информацию о блокировке
            self.blocked_users[str(user_id)] = {
                'user_id': user_id,
                'blocked_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'last_check': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'check_count': 0,
                'reason': 'not_subscribed'
            }
            self.db.set("SubChecker", "blocked_users", self.blocked_users)

            return True
        except Exception as e:
            error_msg = str(e)
            if "FLOOD_WAIT" in error_msg:
                wait_time = error_msg.split("_")[-1]
                raise Exception(f"Превышен лимит запросов. Подождите {wait_time} секунд.")
            elif "USER_BLOCKED" in error_msg or "CONTACT_ID_INVALID" in error_msg:
                # Пользователь уже заблокирован, но нет в нашем списке
                self.blocked_users[str(user_id)] = {
                    'user_id': user_id,
                    'blocked_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'last_check': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'check_count': 0,
                    'reason': 'already_blocked'
                }
                self.db.set("SubChecker", "blocked_users", self.blocked_users)
                return True
            else:
                raise Exception(f"Не удалось заблокировать: {error_msg}")

    async def unblock_user(self, user_id, reason="подписался на канал"):
        """Разблокировка пользователя с обработкой ошибок"""
        # Проверка на флуд
        if self.check_flood_limit(user_id):
            raise Exception("Слишком частые операции. Подождите 2 секунды.")

        user_id_str = str(user_id)

        try:
            await self.client(UnblockRequest(id=user_id))

            # Удаляем из списка заблокированных
            if user_id_str in self.blocked_users:
                del self.blocked_users[user_id_str]
                self.db.set("SubChecker", "blocked_users", self.blocked_users)

            # Удаляем сообщение о подписке если есть
            if user_id_str in self.not_subscribed_msgs:
                await self.delete_not_subscribed_msg(user_id)

            # Отправляем сообщение о разблокировке
            try:
                await self.client.send_message(
                    user_id,
                    self.strings['subscribed']
                )
            except Exception as e:
                print(f"Не удалось отправить сообщение о разблокировке: {e}")

            print(f"Пользователь {user_id} разблокирован: {reason}")
            return True
        except Exception as e:
            error_msg = str(e)
            if "FLOOD_WAIT" in error_msg:
                wait_time = error_msg.split("_")[-1]
                raise Exception(f"Превышен лимит запросов. Подождите {wait_time} секунд.")
            elif "USER_NOT_BLOCKED" in error_msg or "USER_NOT_MUTUAL_CONTACT" in error_msg:
                # Пользователь уже разблокирован
                if user_id_str in self.blocked_users:
                    del self.blocked_users[user_id_str]
                    self.db.set("SubChecker", "blocked_users", self.blocked_users)
                return True
            else:
                raise Exception(f"Не удалось разблокировать: {error_msg}")

    async def check_subscription(self, user_id):
        """Проверка подписки пользователя на канал (оптимизированная)"""
        if not self.channel_id:
            return False

        try:
            # Получаем последних 20 участников и проверяем среди них
            participants = await self.client.get_participants(self.channel_id, limit=20)
            return any(participant.id == user_id for participant in participants)
        except Exception as e:
            print(f"Ошибка проверки подписки: {e}")
            return False

    def is_bot(self, user):
        """Проверка, является ли пользователь ботом"""
        if isinstance(user, User):
            return user.bot
        return False

    def is_whitelisted(self, user_id):
        """Проверка, находится ли пользователь в белом списке"""
        return str(user_id) in self.whitelist

    def add_to_whitelist(self, user_id, added_by=None):
        """Добавление пользователя в белый список"""
        self.whitelist[str(user_id)] = {
            'added_by': added_by,
            'added_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'user_id': user_id
        }
        self.db.set("SubChecker", "whitelist", self.whitelist)

        # Если пользователь был заблокирован - разблокируем
        if str(user_id) in self.blocked_users:
            asyncio.create_task(self.unblock_user(user_id, "добавлен в белый список"))

    def remove_from_whitelist(self, user_id):
        """Удаление пользователя из белого списка"""
        if str(user_id) in self.whitelist:
            del self.whitelist[str(user_id)]
            self.db.set("SubChecker", "whitelist", self.whitelist)
            return True
        return False

    async def save_not_subscribed_msg(self, user_id, message_id):
        """Сохранение ID сообщения о неподписке"""
        self.not_subscribed_msgs[str(user_id)] = message_id
        self.db.set("SubChecker", "not_subscribed_msgs", self.not_subscribed_msgs)

    async def delete_not_subscribed_msg(self, user_id):
        """Удаление сообщения о неподписке"""
        if str(user_id) in self.not_subscribed_msgs:
            try:
                await self.client.delete_messages(user_id, self.not_subscribed_msgs[str(user_id)])
            except Exception as e:
                print(f"Не удалось удалить сообщение: {e}")
            del self.not_subscribed_msgs[str(user_id)]
            self.db.set("SubChecker", "not_subscribed_msgs", self.not_subscribed_msgs)

    def get_not_subscribed_message(self):
        """Получение сообщения о неподписке"""
        if self.custom_message:
            if self.channel_link:
                channel_display = f'<a href="{self.channel_link}">{self.channel_username or "наш канал"}</a>'
            else:
                channel_display = self.channel_username or "наш канал"
            return self.custom_message.replace("{channel_link}", channel_display)

        if self.channel_link:
            channel_display = f'<a href="{self.channel_link}">{self.channel_username or "наш канал"}</a>'
        else:
            channel_display = self.channel_username or "наш канал"

        return self.strings['not_subscribed'].format(channel_link=channel_display)

    def clean_username(self, username):
        """Очистка юзернейма от лишних символов"""
        if not username:
            return ""

        # Убираем все символы @ в начале
        while username.startswith('@'):
            username = username[1:]

        # Убираем URL префиксы
        if username.startswith('https://t.me/'):
            username = username.replace('https://t.me/', '')
        elif username.startswith('t.me/'):
            username = username.replace('t.me/', '')

        # Убираем пробелы
        username = username.strip()

        return username

    @loader.command()
    async def subwl(self, message):
        """Управление белым списком"""
        args = utils.get_args_raw(message)

        if not args:
            # Показать статус белого списка
            total_users = len(self.whitelist)
            status = f"<b>Белый список:</b> {total_users} пользователей\n\n"
            status += "<b>Команды:</b>\n"
            status += ".subwl add [ID] - добавить пользователя\n"
            status += ".subwl remove [ID] - удалить пользователя\n"
            status += ".subwl list - показать список\n"
            status += ".subwl clear - очистить список\n"
            status += ".subwl check [ID] - проверить пользователя\n"
            await utils.answer(message, status)
            return

        parts = args.split(" ", 1)
        command = parts[0].lower()

        if command == "add":
            if len(parts) < 2 and not message.is_reply:
                await utils.answer(message,
                                   "<b>Используйте:</b> .subwl add [ID]\n<b>Или ответьте на сообщение пользователя:</b> .subwl add")
                return

            # Проверка, есть ли reply
            if message.is_reply:
                reply = await message.get_reply_message()
                user = await reply.get_sender()
                user_id = user.id
            else:
                try:
                    user_id = int(parts[1])
                except ValueError:
                    await utils.answer(message, self.strings['invalid_user_id'])
                    return

            # Проверка, не в белом списке ли уже
            if self.is_whitelisted(user_id):
                await utils.answer(message, f"<b>Пользователь уже в белом списке!</b>\n\nID: <code>{user_id}</code>")
                return

            # Добавление в белый список
            self.add_to_whitelist(user_id, message.sender_id)
            await utils.answer(message, self.strings['whitelist_added'].format(user_id))

            # Если у пользователя было сообщение о подписке, удаляем его
            if str(user_id) in self.not_subscribed_msgs:
                await self.delete_not_subscribed_msg(user_id)
                await message.respond(
                    f"<b>Пользователь добавлен в белый список и разблокирован!</b>\n\nID: <code>{user_id}</code>")

        elif command == "remove":
            if len(parts) < 2 and not message.is_reply:
                await utils.answer(message,
                                   "<b>Используйте:</b> .subwl remove [ID]\n<b>Или ответьте на сообщение пользователя:</b> .subwl remove")
                return

            # Проверка, есть ли reply
            if message.is_reply:
                reply = await message.get_reply_message()
                user = await reply.get_sender()
                user_id = user.id
            else:
                try:
                    user_id = int(parts[1])
                except ValueError:
                    await utils.answer(message, self.strings['invalid_user_id'])
                    return

            # Удаление из белого списка
            if self.remove_from_whitelist(user_id):
                await utils.answer(message, self.strings['whitelist_removed'].format(user_id))
            else:
                await utils.answer(message, self.strings['whitelist_not_found'])

        elif command == "list":
            if not self.whitelist:
                await utils.answer(message, self.strings['whitelist_empty'])
                return

            text = "<b>Белый список пользователей:</b>\n\n"
            count = 0

            for user_id_str, data in self.whitelist.items():
                try:
                    user_id = int(user_id_str)
                    user_info = f"<b>ID:</b> <code>{user_id}</code>\n"
                    user_info += f"<b>Добавлен:</b> {data.get('added_at', 'Неизвестно')}\n"

                    # Попробуем получить имя пользователя
                    try:
                        user = await self.client.get_entity(user_id)
                        name = f"{user.first_name or ''} {user.last_name or ''}".strip() or user.username or "Неизвестно"
                        user_info += f"<b>Имя:</b> {name}\n"
                    except Exception as e:
                        user_info += f"<b>Имя:</b> Не удалось получить\n"

                    text += user_info + "─" * 20 + "\n"
                    count += 1

                    # Ограничим вывод чтобы не превысить лимит сообщения
                    if count >= 20:
                        text += f"\n<b>И еще:</b> {len(self.whitelist) - count} пользователей..."
                        break

                except Exception as e:
                    continue

            text = self.strings['whitelist_list'].format(f"Всего: {len(self.whitelist)}\n\n") + text
            await utils.answer(message, text)

        elif command == "clear":
            count = len(self.whitelist)
            self.whitelist = {}
            self.db.set("SubChecker", "whitelist", self.whitelist)
            await utils.answer(message, self.strings['whitelist_cleared'].format(count))

        elif command == "check":
            if len(parts) < 2 and not message.is_reply:
                await utils.answer(message,
                                   "<b>Используйте:</b> .subwl check [ID]\n<b>Или ответьте на сообщение пользователя:</b> .subwl check")
                return

            # Проверка, есть ли reply
            if message.is_reply:
                reply = await message.get_reply_message()
                user = await reply.get_sender()
                user_id = user.id
            else:
                try:
                    user_id = int(parts[1])
                except ValueError:
                    await utils.answer(message, self.strings['invalid_user_id'])
                    return

            # Проверка наличия в белом списке
            if self.is_whitelisted(user_id):
                data = self.whitelist[str(user_id)]
                await utils.answer(message, self.strings['user_in_whitelist'].format(
                    user_id,
                    data.get('added_at', 'Неизвестно')
                ))
            else:
                await utils.answer(message, self.strings['user_not_in_whitelist'])

        else:
            await utils.answer(message, "<b>Неизвестная команда!</b>\n\nИспользуйте .subwl для списка команд")

    @loader.command()
    async def submessage(self, message):
        """Кастомное сообщение, используйте {channel_link} """
        args = utils.get_args_raw(message)

        if not args:
            if not self.custom_message:
                await utils.answer(message, self.strings['no_custom_message'])
            else:
                await utils.answer(message,
                                   self.strings['current_custom_message'].format(self.custom_message)
                                   )
            return

        self.custom_message = args
        self.db.set("SubChecker", "custom_message", self.custom_message)

        await utils.answer(message, self.strings['custom_message_set'])

    @loader.command()
    async def submessageclear(self, message):
        """Сбросить кастомное сообщение"""
        self.custom_message = ""
        self.db.set("SubChecker", "custom_message", self.custom_message)

        await utils.answer(message, self.strings['custom_message_cleared'])

    @loader.command()
    async def subchannel(self, message):
        """Настроить канал для проверки подписки [юзернейм или ссылка]"""
        args = utils.get_args_raw(message)

        if not args:
            if not self.channel_username:
                await utils.answer(message, self.strings['channel_not_set'])
            else:
                channel_info = f"@{self.channel_username}" if not self.channel_username.startswith(
                    '@') else self.channel_username
                if self.channel_link:
                    channel_info = f"<a href='{self.channel_link}'>{channel_info}</a>"

                await utils.answer(message,
                                   self.strings['current_channel'].format(
                                       channel_info,
                                       self.channel_id if self.channel_id else "Не определен"
                                   )
                                   )
            return

        # Очищаем username
        cleaned_username = self.clean_username(args)

        try:
            channel = await self.client.get_entity(cleaned_username)

            self.channel_username = f"@{channel.username}" if hasattr(channel,
                                                                      'username') and channel.username else cleaned_username
            self.channel_id = channel.id

            if hasattr(channel, 'username') and channel.username:
                self.channel_link = f"https://t.me/{channel.username}"
            else:
                self.channel_link = f"tg://resolve?domain={cleaned_username}"

            self.db.set("SubChecker", "channel_username", self.channel_username)
            self.db.set("SubChecker", "channel_link", self.channel_link)
            self.db.set("SubChecker", "channel_id", self.channel_id)

            channel_display = f"@{channel.username}" if hasattr(channel,
                                                                'username') and channel.username else cleaned_username
            channel_info = f"<a href='{self.channel_link}'>{channel_display}</a>"

            await utils.answer(message,
                               self.strings['channel_set'].format(channel_info)
                               )

            # Перезапускаем фоновую проверку при смене канала
            await self.stop_background_checker()

            if self.enabled and self.channel_id:
                await self.start_background_checker()

        except Exception as e:
            await utils.answer(message,
                               self.strings['invalid_channel'] + f"\n\n<code>{str(e)}</code>"
                               )

    @loader.command()
    async def subtest(self, message):
        """Протестировать доступ к каналу"""
        if not self.channel_id:
            await utils.answer(message, self.strings['channel_not_set'])
            return

        try:
            channel = await self.client.get_entity(self.channel_id)
            participants = await self.client.get_participants(self.channel_id, limit=5)

            channel_info = []
            if hasattr(channel, 'title'):
                channel_info.append(f"<b>Название:</b> {channel.title}")
            if hasattr(channel, 'username'):
                channel_info.append(f"<b>Юзернейм:</b> @{channel.username}")
            channel_info.append(f"<b>ID:</b> <code>{channel.id}</code>")
            channel_info.append(f"<b>Участников (последние 5):</b> {len(participants)}")

            await utils.answer(message,
                               self.strings['test_success'] + "\n\n" + "\n".join(channel_info)
                               )

        except Exception as e:
            error_msg = str(e)
            if "CHANNEL_PRIVATE" in error_msg or "аналог is private" in error_msg:
                error_msg = self.strings['no_permission']

            await utils.answer(message,
                               self.strings['test_failed'].format(error_msg)
                               )

    @loader.command()
    async def subcheck(self, message):
        """Включить/выключить проверку подписки"""
        args = utils.get_args_raw(message)

        if args.lower() == "on":
            if not self.channel_id:
                await utils.answer(message, self.strings['channel_not_set'])
                return

            self.db.set("SubChecker", "enabled", True)
            self.enabled = True

            # Запускаем фоновую проверку
            await self.start_background_checker()

        elif args.lower() == "off":
            self.db.set("SubChecker", "enabled", False)
            self.enabled = False

            # Останавливаем фоновую проверку
            await self.stop_background_checker()

        status_text = "Включена" if self.enabled else "Выключена"
        channel_status = "Настроен" if self.channel_id else "Не настроен"
        whitelist_status = f"{len(self.whitelist)} пользователей"
        blocked_status = f"{len(self.blocked_users)} пользователей"

        response = "<b>Статус проверки подписки:</b>\n\n"
        response += f"<b>Проверка:</b> {status_text}\n"
        response += f"<b>Канал:</b> {channel_status}\n"
        response += f"<b>Белый список:</b> {whitelist_status}\n"
        response += f"<b>Заблокировано:</b> {blocked_status}\n"
        response += f"<b>Интервал проверки:</b> {self.check_interval} сек\n"

        if self.channel_username:
            response += f"<b>Текущий канал:</b> {self.channel_username}\n"

        response += "\n<b>Основные команды:</b>\n"
        response += ".subcheck on/off - вкл/выкл проверку\n"
        response += ".subchannel @юзернейм - установить канал\n"
        response += ".submessage текст - кастомное сообщение\n"
        response += ".subwl - управление белым списком\n"
        response += ".subinterval N - интервал проверки (сек)\n"
        response += ".subblocked - список заблокированных\n"
        response += ".subforcecheck - принудительная проверка\n"

        await utils.answer(message, response)

    @loader.command()
    async def subinterval(self, message):
        """Установить интервал проверки подписок (в секундах, минимум 30)"""
        args = utils.get_args_raw(message)

        if not args:
            await utils.answer(message,
                               self.strings['current_check_interval'].format(self.check_interval)
                               )
            return

        try:
            interval = int(args)
            if interval < 30:
                interval = 30

            self.check_interval = interval
            self.db.set("SubChecker", "check_interval", interval)

            await utils.answer(message,
                               self.strings['check_interval_set'].format(interval)
                               )

            # Перезапускаем фоновую задачу если она работает
            if self.check_running:
                await self.stop_background_checker()
                await self.start_background_checker()

        except ValueError:
            await utils.answer(message, self.strings['invalid_interval'])

    @loader.command()
    async def subblocked(self, message):
        """Показать список заблокированных пользователей"""
        args = utils.get_args_raw(message)

        if not self.blocked_users:
            await utils.answer(message, self.strings['no_blocked_users'])
            return

        if args:
            # Информация о конкретном пользователе
            try:
                user_id = int(args)
                user_id_str = str(user_id)

                if user_id_str not in self.blocked_users:
                    await utils.answer(message,
                                       f"<b>Пользователь не найден в списке заблокированных!</b>\n\nID: <code>{user_id}</code>")
                    return

                data = self.blocked_users[user_id_str]

                # Получаем информацию о пользователе
                try:
                    user = await self.client.get_entity(user_id)
                    name = f"{user.first_name or ''} {user.last_name or ''}".strip() or user.username or str(user_id)
                    user_info = f"<b>Имя:</b> {name}\n"
                except Exception as e:
                    user_info = ""

                info = self.strings['blocked_user_info'].format(
                    user_id,
                    data.get('blocked_at', 'Неизвестно'),
                    data.get('check_count', 0),
                    data.get('last_check', 'Никогда')
                )

                info = user_info + info

                # Проверяем текущий статус подписки
                is_subscribed = await self.check_subscription(user_id)
                sub_status = "Подписан" if is_subscribed else "Не подписан"
                info += f"\n<b>Текущий статус подписки:</b> {sub_status}"

                await utils.answer(message, info)

            except ValueError:
                await utils.answer(message, self.strings['invalid_user_id'])
            return

        # Показываем список всех заблокированных
        text = f"<b>Заблокировано пользователей:</b> {len(self.blocked_users)}\n\n"

        count = 0
        for user_id_str, data in self.blocked_users.items():
            try:
                user_id = int(user_id_str)
                try:
                    user = await self.client.get_entity(user_id)
                    name = f"{user.first_name or ''} {user.last_name or ''}".strip() or user.username or str(user_id)
                except Exception as e:
                    name = str(user_id)

                blocked_time = data.get('blocked_at', 'Неизвестно')
                check_count = data.get('check_count', 0)

                text += f"<b>{name}</b>\nID: <code>{user_id}</code>\nЗаблокирован: {blocked_time}\nПроверок: {check_count}\n"
                text += "─" * 20 + "\n"

                count += 1
                if count >= 15:  # Ограничим вывод
                    remaining = len(self.blocked_users) - count
                    text += f"\n<b>И еще {remaining} пользователей...</b>"
                    break

            except Exception as e:
                continue

        text += f"\n<b>Интервал проверки:</b> {self.check_interval} секунд"
        text += f"\n<b>Используйте:</b> .subblocked [ID] для подробной информации"

        await utils.answer(message, text)

    @loader.command()
    async def subforcecheck(self, message):
        """Принудительная проверка всех заблокированных пользователей"""
        if not self.channel_id:
            await utils.answer(message, self.strings['channel_not_set'])
            return

        if not self.blocked_users:
            await utils.answer(message, self.strings['no_blocked_users'])
            return

        await utils.answer(message,
                           self.strings['force_check_started'].format(len(self.blocked_users))
                           )

        unblocked_count = 0
        checked_count = 0

        # Получаем участников канала (только последние 20)
        try:
            participant_ids = await self.get_channel_participants()
        except Exception as e:
            await utils.answer(message, f"<b>Ошибка получения участников канала:</b>\n\n<code>{str(e)}</code>")
            return

        # Проверяем каждого заблокированного пользователя
        for user_id_str in list(self.blocked_users.keys()):
            user_id = int(user_id_str)
            checked_count += 1

            # Пропускаем если пользователь в белом списке
            if self.is_whitelisted(user_id):
                try:
                    await self.unblock_user(user_id, "пользователь в белом списке")
                    unblocked_count += 1
                except Exception as e:
                    print(f"Ошибка при разблокировке пользователя {user_id}: {e}")
                continue

            # Проверяем подписку
            if user_id in participant_ids:
                # Пользователь подписался - разблокируем
                try:
                    await self.unblock_user(user_id, "подписался на канал")
                    unblocked_count += 1
                except Exception as e:
                    print(f"Ошибка при разблокировке пользователя {user_id}: {e}")
            else:
                # Обновляем счетчик проверок
                self.blocked_users[user_id_str]['check_count'] = self.blocked_users[user_id_str].get('check_count',
                                                                                                     0) + 1
                self.blocked_users[user_id_str]['last_check'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.db.set("SubChecker", "blocked_users", self.blocked_users)

        still_blocked = len(self.blocked_users)

        result = self.strings['check_complete'].format(
            checked_count,
            unblocked_count,
            still_blocked
        )

        await utils.answer(message, result)

    @loader.command()
    async def sublist(self, message):
        """Показать список пользователей с сообщениями о подписке"""
        if not self.not_subscribed_msgs:
            await utils.answer(message, "Нет пользователей с активными сообщениями о подписке")
            return

        text = "<b>Пользователи с сообщениями о подписке:</b>\n\n"
        count = 0
        for user_id_str in self.not_subscribed_msgs:
            user_id = int(user_id_str)
            try:
                user = await self.client.get_entity(user_id)
                name = f"{user.first_name or ''} {user.last_name or ''}".strip() or user.username or str(user_id)

                is_subscribed = await self.check_subscription(user_id)
                sub_status = "Подписан" if is_subscribed else "Не подписан"
                whitelist_status = "В белом списке" if self.is_whitelisted(user_id) else "Не в белом списке"
                blocked_status = "Заблокирован" if str(user_id) in self.blocked_users else "Не заблокирован"

                text += f"{name} (ID: {user_id})\nСтатус: {sub_status}, {whitelist_status}, {blocked_status}\n"
                count += 1
            except Exception as e:
                text += f"ID: {user_id}\n"
                count += 1

        text += f"\n<b>Всего:</b> {count}\n\n"
        text += f"Сообщения автоматически удаляются после подписки на канал"

        await utils.answer(message, text)

    @loader.command()
    async def subclean(self, message):
        """Очистить все сообщения о подписке"""
        count = 0
        for user_id_str in list(self.not_subscribed_msgs.keys()):
            user_id = int(user_id_str)
            try:
                await self.client.delete_messages(user_id, self.not_subscribed_msgs[user_id_str])
                count += 1
            except Exception as e:
                print(f"Не удалось удалить сообщение для пользователя {user_id}: {e}")

        self.not_subscribed_msgs = {}
        self.db.set("SubChecker", "not_subscribed_msgs", self.not_subscribed_msgs)

        await utils.answer(message, f"<b>Удалено {count} сообщений о подписке</b>")

    async def watcher(self, message):
        """Обработчик входящих сообщений"""

        # Проверка включен ли модуль
        if not self.enabled:
            return

        # Проверка настроен ли канал
        if not self.channel_id:
            return

        # Проверка что сообщение в личке
        if not message.is_private:
            return

        # Проверка что сообщение не исходящее
        if message.out:
            return

        # Получение информации об отправителе
        try:
            user = await message.get_sender()
        except Exception as e:
            print(f"Ошибка получения отправителя: {e}")
            return

        # Проверка что отправитель не бот
        if self.is_bot(user):
            print(f"Бот обнаружен: {user.id}")
            return

        user_id = user.id

        # Проверка белого списка
        if self.is_whitelisted(user_id):
            print(f"Пользователь в белом списке: {user_id}")
            # Если пользователь был заблокирован, разблокируем
            if str(user_id) in self.blocked_users:
                try:
                    await self.unblock_user(user_id, "пользователь в белом списке")
                except Exception as e:
                    print(f"Ошибка разблокировки пользователя {user_id}: {e}")
            return

        print(f"Проверка пользователя: {user_id}")

        # Проверка подписки
        is_subscribed = await self.check_subscription(user_id)
        print(f"Пользователь {user_id} подписан: {is_subscribed}")

        # Если подписан
        if is_subscribed:
            print(f"Пользователь {user_id} подписан, обработка...")
            if str(user_id) in self.not_subscribed_msgs:
                await self.delete_not_subscribed_msg(user_id)
                try:
                    await message.respond(self.strings['subscribed'])
                except Exception as e:
                    print(f"Не удалось отправить сообщение: {e}")

            # Если пользователь был заблокирован, разблокируем
            if str(user_id) in self.blocked_users:
                print(f"Пользователь {user_id} был заблокирован, разблокируем...")
                try:
                    await self.unblock_user(user_id, "подписался на канал")
                except Exception as e:
                    print(f"Ошибка разблокировки пользователя {user_id}: {e}")

            return

        # Если не подписан
        print(f"Пользователь {user_id} не подписан, блокируем...")
        try:
            # Блокируем пользователя
            await self.block_user(user_id)
            print(f"Пользователь {user_id} заблокирован")

            # Отправляем сообщение о блокировке
            if str(user_id) not in self.not_subscribed_msgs:
                message_text = self.get_not_subscribed_message()
                sent_msg = await message.respond(message_text)
                await self.save_not_subscribed_msg(user_id, sent_msg.id)
                print(f"Сообщение о блокировке отправлено пользователю {user_id}")

            await message.delete()
            print(f"Сообщение от пользователя {user_id} удалено")

        except Exception as e:
            error_msg = str(e)
            print(f"Ошибка при блокировке пользователя {user_id}: {error_msg}")

    # При выключении модуля останавливаем фоновую задачу
    async def on_unload(self):
        await self.stop_background_checker()
