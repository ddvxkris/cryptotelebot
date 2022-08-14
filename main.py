from threading import Thread
from time import sleep
import os

try:
    import telebot
    from telebot import types
    import requests
    from bs4 import BeautifulSoup
except ModuleNotFoundError:
    os.system('pip install requests pyTelegramBotAPI BeautifulSoup4')
    from telebot import types
    import requests
    from bs4 import BeautifulSoup

class UserData:
    def __init__(self, username: str):
        self.username = username
    username: str
    text_type: str = "start"

user_datas = []
# ищет в user_datas данные пользователя по его нику
def find_user_data_index(username: str) -> int:
    for index in range(0, len(user_datas)):
        if user_datas[index].username == username:
            return index
    return -1  

def handle_user(func):
    def wrapper(message):
        if find_user_data_index(message.from_user.username) == -1:
            user_datas.append(UserData(message.from_user.username))
            print('Новый пользователь начал диалог с ботом')
        func(message)
    return wrapper

if __name__ == '__main__':
    bot = telebot.TeleBot('yourtokenhere')
    
    # функция реагирующея на команды /start и /help, пользователь должен их прописать чтобы пользоваться ботом.
    @bot.message_handler(commands=['start', 'help'])
    def start(message):
        user_index = find_user_data_index(message.from_user.username)
        if user_index == -1:
            user_datas.append(UserData(message.from_user.username))
            user_index = find_user_data_index(message.from_user.username)
        user_datas[user_index].text_type = 'start'

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add('/subscribe', '/unsubscribe')

        bot.send_message(message.chat.id, '<b>Здравствуйте!</b> Я - бот для отслеживания курса криптовалют.\nПоддерживается <b>Биткоин и Эфериум.</b>\nДля рассылки воспользуйтесь командами снизу\n/subscribe /unsubscribe', 'html', reply_markup=markup)

    def check_for_user_sub(currency: str, user_id) -> bool:
        return open(f'{currency}_subs', 'r').read().split().__contains__(str(user_id))

    @bot.message_handler(commands=['subscribe'])
    @handle_user
    def subscribe(message):
        if check_for_user_sub('btc', message.chat.id) and check_for_user_sub('eth', message.chat.id):
            bot.send_message(message.chat.id, 'Вы и так на все подписаны.')
        else:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            if not check_for_user_sub('btc', message.chat.id):
                markup.add('BTC')
            if not check_for_user_sub('eth', message.chat.id):
                markup.add('ETH')
            markup.add('Назад')
            bot.send_message(message.chat.id, 'Выберите криптовалюту для отслеживания.', reply_markup=markup)
            user_datas[find_user_data_index(message.from_user.username)].text_type = 'select_currency_sub'

    @bot.message_handler(commands=['unsubscribe'])
    @handle_user
    def unsubscribe(message):
        # здесь неплохо было бы сделать функционал для отписки от конкретной валюты
        if not check_for_user_sub('btc', message.chat.id) and not check_for_user_sub('eth', message.chat.id):
            bot.send_message(message.chat.id, 'Вы и так не подписаны.')
        else:
            btc_subs = open('btc_subs', 'r').read().split()
            eth_subs = open('eth_subs', 'r').read().split()
            btc_subs.remove(str(message.chat.id))
            eth_subs.remove(str(message.chat.id))
            open('btc_subs', 'w').write('\n'.join(btc_subs))
            open('eth_subs', 'w').write('\n'.join(eth_subs))
            print('Пользователь отписался от рассылки.')
            bot.send_message(message.chat.id, 'Вы отписались от рассылки.\nЧтобы подписаться, напишите /subscribe')

    @bot.message_handler(content_types=['text'])
    @handle_user
    def text_linker(message):
        user_index = find_user_data_index(message.from_user.username)
        if user_datas[user_index].text_type == 'start' or message.text == 'Назад':
            start(message)
        elif user_datas[user_index].text_type == 'select_currency_sub':
            if message.text == 'BTC' or message.text == 'ETH':
                if not open(f'{message.text.lower()}_subs', 'r').read().split().__contains__(str(message.chat.id)):
                    open(f'{message.text.lower()}_subs', 'a').write(str(message.chat.id) + '\n')
                    bot.send_message(message.chat.id, f'Вы подписались на рассылку курса {message.text}!\nЧтобы отписаться, напишите /unsubscribe')
                    print(f'Новый пользователь подписался на рассылку {message.text}')
                start(message)
            else:
                bot.send_message(message.chat.id, 'Пожалуйста, напишите криптовалюту для отслеживания (BTC или ETH)')
        else:
            bot.send_message(message.chat.id, 'Извините, не понял вас.\n/help')

    def run_tracking():
        # основная функция бота, отслеживает курс криптовалюты с помощью парсинга.
        def track_price(currency: str):
            price_selector = 'YMlKec fxKbKc'

            def get_page():
                nonlocal currency
                return requests.get(f'https://www.google.com/finance/quote/{currency}-RUB').content

            html = get_page()

            def get_price(refresh: bool = True) -> float:
                nonlocal html
                if refresh:
                    html = get_page()
                return float(BeautifulSoup(html, 'html.parser').find('div', class_ = price_selector).text.replace(',', ''))

            old_price = get_price(False)

            while True:
                sleep(30)
                price = get_price()
                delta = price - old_price
                if delta < 0:
                    delta *= -1
                if delta >= old_price / 2000:
                    delta_percent = delta / (old_price / 100)
                    indicator = '+' if price > old_price else '-'
                    for chat_id in open(f'{currency.lower()}_subs', 'r').read().split():
                        bot.send_message(chat_id, f'{currency}: {indicator}{delta} ({indicator}{str(delta_percent)[0:6]}%)', disable_notification=False)
                    old_price = get_price()
                else:
                    last_update = BeautifulSoup(html, 'html.parser').select('div.ygUjEc')[0].text
                    print(f"{currency}: Нет изменений. Последнее обновление курса: {last_update.replace(' · Disclaimer', '')}")
        # стоит пояснить:
        # я использую потоки вместо async функций так как это банально проще. 
        # Здесь раньше был async, но я его убрал из-за того что так не работал polling, так как telebot не поддерживает ассинхрон,
        # а переходить на библиотеку типа aiogram ради 3 строк кода мне не хотелось. 
        # Но перешел бы, если проект имел бы больший масштаб и требовал обновлений спустя время.
        Thread(target=lambda: track_price('BTC'), daemon = True).start()
        Thread(target=lambda: track_price('ETH'), daemon = True).start()
    
    run_tracking()
    bot.polling(True)