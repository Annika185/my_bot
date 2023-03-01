import telebot
import requests
import datetime
import os


class APIException(Exception):
    """Исключения, возникающие при общении с ботом"""
    def __init__(self, *args):
        if args:
            self.message = args[0]
        else:
            self.message = None

    def __str__(self):
        if self.message:
            return 'APIException. {0} '.format(self.message)
        else:
            return 'APIException has been raised'


class Currency:
    """Класс описывающий методы общения с внешним API для получения курса валют и формирования ответов бота"""
    def __init__(self):
        self.currency_data = None
        self.last_update = None
        self.data_update()

    def data_update(self):
        """Обновляет данные о курсах валют"""
        self.currency_data = requests.get('https://www.cbr-xml-daily.ru/daily_json.js').json()
        # Все курсы валют в рублях, а самого рубля в данных нет. Добавим его
        self.currency_data['Valute']['RUB'] = {
            'CharCode': 'RUB', 'Nominal': 1, 'Name': 'Российский рубль', 'Value': 1, 'Previous': 1
        }
        self.last_update = datetime.datetime.fromisoformat(self.currency_data['Date'])

    def calc_exchange(self, base: str, quote: str, amount: float) -> float:
        """Рассчитывает обмен некоторого количества (amount) базовой валюты (base) на нужную валюту (quote)
           Возвращает стоимость"""
        base_valute = self.currency_data['Valute'][base]
        quote_valute = self.currency_data['Valute'][quote]
        price = (amount * base_valute['Value'] / base_valute['Nominal']) / (
                    quote_valute['Value'] / quote_valute['Nominal'])
        return price

    def get_currencies(self) -> str:
        """Возвращает список доступных валют в виде многострочного текста"""
        valutes = self.currency_data['Valute']
        text = 'Используйте коды валют при запросах боту. Доступные валюты и их коды:\n'
        for currency in valutes:
            if valutes[currency]['Nominal'] == 1:
                name = valutes[currency]['Name']
            else:
                name = 'для ' + valutes[currency]['Name']

            text += '{0} - {1}\n'.format(
                valutes[currency]['CharCode'], name)
        return text

    def check_currency(self, *args):
        """Проверяет наличие валют из списка args в полученных данных"""
        for currency_code in args:
            try:
                self.currency_data['Valute'][currency_code]
            except KeyError:
                raise APIException(f'Валюта {currency_code} не доступна или не существует, проверьте правильность ввода')

    def get_price(self, base: str, quote: str, amount: float) -> str:
        """Возвращает строку - ответ бота"""
        self.data_update()
        price = self.calc_exchange(base, quote, amount)

        return f'По курсу ЦБ РФ на {str(self.last_update)} \n{amount} {base} = {price} {quote}'


def parse_msg(msg):
    """Разбиение на аргументы и анализ правильности ввода команды пользователя
       Возвращает список аргументов для рассчета обмена"""
    args = msg.upper().split(' ', maxsplit=2)
    if len(args) == 1 and args[0][0] == '/':
        raise APIException('Неправильная команда, справка по использованию бота:\n/help')
    elif len(args) < 3:
        raise APIException('Недостаточное количество аргументов, справка по использованию бота:\n/help')
    cur.check_currency(args[0], args[1])
    try:
        args[2] = float(args[2].replace(',', '.').replace(' ', ''))
    except Exception:
        raise APIException(f'{args[2]} неправильное значение. Третим аргументом должно быть количество базовой валюты, '
                           f'справка по использованию:\n/help')
    return args


TOKEN = os.getenv('TOKEN')
bot = telebot.TeleBot(TOKEN, parse_mode=None)
cur = Currency()
print(datetime.datetime.now())


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """Ответ на команды /start и /help"""
    answer = cur.get_price('USD', 'RUB', 100.0)
    bot.reply_to(message, 'Для конвертации валют используйте сообщения с кодами валют.\n'
                          'Указывайте сначала базовую валюту, потом валюту, на которую нужно совершить обмен, '
                          'потом количество базовой валюты для обмена\n'
                          'Сообщение долно иметь вид типа "USD RUB 100.00"\n'
                          'Ответ бота будет в виде:\n'
                          f'"{answer}"\n'
                          'Доступные валюты можно посмотреть с помощью команды:\n/values'
                 )


@bot.message_handler(commands=['values'])
def send_values(message):
    """Ответ на команду /values"""
    bot.reply_to(message, cur.get_currencies())


@bot.message_handler(func=lambda m: True)
def send_all(message):
    """Ответ на все остальные сообщения или команды"""
    try:
        base, quote, amount = parse_msg(message.text)
    except APIException as e:
        answer = e
    else:
        answer = cur.get_price(base, quote, amount)
    bot.reply_to(message, answer)


print('Bot online')
bot.infinity_polling()
