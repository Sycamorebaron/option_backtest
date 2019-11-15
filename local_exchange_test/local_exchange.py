from local_exchange_test.util import *
from local_exchange_test.trading_calender import TradingCalender
from local_exchange_test.data_fetcher import DataFetcher
from local_exchange_test.account import Account
from local_exchange_test.option_market import OptionMarket
from local_exchange_test.stock_market import StockMarket


class LocalExchange:
    def __init__(self, init_cash, stock_prop):
        # 50etf 的交易时间作为交易日历
        self.trading_calender = TradingCalender(
            init_index='50etf',
            engine=option_eg
        )
        # 期权数据获取器，base，即基准为不复权的50etf价格，主要用于筛选实值虚值期权
        self.option_data_fetcher = DataFetcher(
            engine=option_eg,
            schema='trading_data',
            base='50etf',
            label='option_code'
        )
        # 股票、指数数据获取器
        self.stock_data_fetcher = DataFetcher(
            engine=stk_eg,
            schema='time_cs',
            base='sh000016',
            label='code'
        )
        # 股票账户
        self.stock_account = Account(
            init_cash=init_cash * stock_prop
        )
        # 期权账户
        self.option_account = Account(
            init_cash=init_cash * (1 - stock_prop)
        )
        # 期权市场。完成一些期权市场特有的操作，比如选择实值虚值期权，选择标准、非标准期权
        self.option_market = OptionMarket(
            data_fetcher=self.option_data_fetcher,
            trading_calender=self.trading_calender
        )
        # 股票市场。完成一些股票市场特有的操作，比如查看涨跌停
        self.stock_market = StockMarket(
            data_fetcher=self.stock_data_fetcher,
            trading_calender=self.trading_calender
        )
        # 手续费，之后可以抽象成Slippage
        self.option_fee = 5
        self.stock_fee = 0.002

    def open_order(self, market, symbol, price, amount, date, check_cash):
        """
        开仓下单，纯开仓或加仓。但反向开仓需要先调用close_order方法平仓，再用本方法开仓
        :param market:
        :param symbol:
        :param price:
        :param amount:
        :param date:
        :return:
        """
        if market == 'option':
            account = self.option_account
            account.cash -= abs(amount) * self.option_fee
        elif market == 'stock':
            account = self.stock_account
            account.cash -= abs(amount) * price * self.stock_fee
        else:
            raise Exception('ACCOUNT NOT SUPPORTED NOW!')

        if (amount > 0) and check_cash:
            if amount * price > account.cash:
                raise Exception('NOT ENOUGH BALANCE WHEN OPEN')

        not_opened = True
        for i in range(len(account.position)):
            pos = account.position[i]
            # 加仓
            if pos['symbol'] == symbol:
                if amount * pos['amount'] < 0:
                    raise Exception('USE CLOSE TO DEC')
                avg_price = (pos['open_price'] * abs(pos['amount']) + price * abs(amount)) / \
                            (abs(pos['amount']) + abs(amount))
                account.position[i]['open_price'] = avg_price
                account.position[i]['amount'] += amount
                not_opened = False

        # 纯开仓
        if not_opened:
            account.position.append({
                'open_date': date,
                'symbol': symbol,
                'open_price': price,
                'amount': amount,
                'pnl': 0
            })

    def close_order(self, market, symbol, price, amount, contract_num=1):
        """
        平仓下单，纯平仓或减仓。反向开仓时先调用本方法平仓，再调用open_order方法开仓
        :param market:
        :param symbol:
        :param price:
        :param amount:
        :return:
        """
        if market == 'option':
            account = self.option_account
            account.cash -= abs(amount) * self.option_fee
        elif market == 'stock':
            account = self.stock_account
            account.cash -= abs(amount) * price * self.stock_fee
        else:
            raise Exception('ACCOUNT NOT SUPPORTED NOW!')

        for i in range(len(account.position)):
            pos = account.position[i]
            if not pos:
                continue
            # 减仓或平仓
            if pos['symbol'] == symbol:
                if amount * pos['amount'] > 0:
                    raise Exception('USE OPEN TO INC')
                elif abs(amount) > abs(pos['amount']):
                    print(market, symbol, price, amount)
                    raise Exception('NOT ENOUGH POSITION TO CLOSE')

                account.cash += -amount * (price - pos['open_price']) * contract_num  # 如果是期权，这里需要乘以!=1的合约单位
                account.position[i]['amount'] += amount

                account.position[i]['pnl'] = account.position[i]['pnl'] * abs(account.position[i]['amount']) / (abs(account.position[i]['amount']) + abs(amount))

            # 如果全部减仓完了，说明是完全平仓，清除记录
            if account.position[i]['amount'] == 0:
                account.position[i] = {}

    def equity(self, date):
        """
        用当天的收盘价计算当天的总权益，权益 = 现金 + 浮动盈亏
        :return:
        """
        self.bookkeeping(date=date)

        now_equity = 0
        for account in [self.option_account, self.stock_account]:
            now_equity += account.cash
            for pos in account.position:
                now_equity += pos['pnl']
        return now_equity

    def bookkeeping(self, date):
        """
        用当天的收盘价计算浮动盈亏
        :param date:
        :return:
        """
        while {} in self.option_account.position:
            self.option_account.position.remove({})
        while {} in self.stock_account.position:
            self.stock_account.position.remove({})

        d_option_price = self.option_data_fetcher.get_all_symbol_field(
            date=date,
            field=['close']
        )
        d_stock_price = self.stock_data_fetcher.get_all_symbol_field(
            date=date,
            field=['close']
        )

        for i in range(len(self.option_account.position)):
            pos = self.option_account.position[i]
            if date < pos['open_date']:
                raise Exception('BOOKKEEPING DATE EARLIER THAM OPEN DATE')
            price = d_option_price[pos['symbol']]
            self.option_account.position[i]['pnl'] = (price - pos['open_price']) * pos['amount'] * 10000

        print('当前期权账户情况\n', self.option_account, '\n')
        for j in range(len(self.stock_account.position)):
            pos = self.stock_account.position[j]
            if date < pos['open_date']:
                raise Exception('BOOKKEEPING DATE EARLIER THAM OPEN DATE')
            print(pos)
            price = d_stock_price[pos['symbol']]
            self.stock_account.position[j]['pnl'] = (price - pos['open_price']) * pos['amount']

        print('当前股票账户情况\n', self.stock_account, '\n')

if __name__ == '__main__':

    local_exchange = LocalExchange(init_cash=10000000)
    local_exchange.open_order(
        market='option',
        symbol='10001966',
        price=local_exchange.option_data_fetcher.get_symbol_field(
            symbol='10001966',
            date=pd.to_datetime('2019-10-21'),
            field=['open']
        )['open'],
        amount=100,
        date=pd.to_datetime('2019-10-31'),
        check_cash=False
    )
    print(local_exchange.option_account)

    local_exchange.close_order(
        market='option',
        symbol='10001966',
        price=local_exchange.option_data_fetcher.get_symbol_field(
            symbol='10001966',
            date=pd.to_datetime('2019-10-31'),
            field=['open']
        )['open'],
        amount=-10
    )
    print(local_exchange.option_account)
