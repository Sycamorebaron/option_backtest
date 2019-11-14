from local_exchange_test.util import *

class StockMarket:
    def __init__(self, data_fetcher, trading_calender):
        self.data_fetcher = data_fetcher
        self.trading_calender = trading_calender

    def if_tradable(self, date, symbol, buy_or_sell):
        """
        查看是否可交易，涨跌停
        :param date:
        :param symbol:
        :param buy_or_sell:
        :return:
        """
        last_close = self.data_fetcher.get_symbol_field(
            symbol=symbol,
            date=self.trading_calender.get_last_trading_date(date=date),
            field=['close']
        )['close']
        this_open = self.data_fetcher.get_symbol_field(
            symbol=symbol,
            date=date,
            field=['open']
        )['open']
        if buy_or_sell == 'buy':
            if (this_open / last_close - 1) > 0.098:
                return False
            else:
                return True
        else:
            if (this_open / last_close - 1) < -0.098:
                return False
            else:
                return True

    def cal_open_amount(self, date, symbol, money, fee):
        """
        用开盘价计算可开数量
        :param date:
        :param symbol:
        :param money:
        :return:
        """
        price = self.data_fetcher.get_symbol_field(
            symbol=symbol,
            date=date,
            field=['open']
        )['open']
        print(symbol, '开仓价格', price)
        return int(money * (1 / (1 + fee)) / (price * 100)) * 100

