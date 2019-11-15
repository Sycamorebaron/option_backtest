from local_exchange_test.util import *
from local_exchange_test.earth_calender import EarthCalender
from local_exchange_test.local_exchange import LocalExchange
from matplotlib import pyplot as plt

"""

交易逻辑在Agent里展开。

"""


class Agent:
    def __init__(self, cash, begin, end, if_draw_pic, stock_prop, fig_name, check_individual_account):
        self.earth_calender = EarthCalender(
            begin=begin,
            end=end
        )
        self.local_exchange = LocalExchange(
            init_cash=cash,
            stock_prop=stock_prop
        )
        self.check_individual_account = check_individual_account  # True / False 股票账户和期权账户是否要分开计量
        self.stock_prop = stock_prop
        self.if_draw_pic = if_draw_pic
        self.equity_curve = []
        self.monthly_rebalanced = False
        self.fig_name = fig_name

    def append_equity(self):
        """
        记录权益信息
        :return:
        """
        self.equity_curve.append(
            {
                'date': self.earth_calender.now,
                'equity': self.local_exchange.equity(date=self.earth_calender.now),
                'base': self.local_exchange.stock_data_fetcher.get_base_price(
                    date=self.earth_calender.now,
                    field='close'
                ),
                'stock': self.local_exchange.stock_account.cash + sum(
                    [i['pnl'] for i in self.local_exchange.stock_account.position]
                ),
                'option': self.local_exchange.option_account.cash + sum(
                    [i['pnl'] for i in self.local_exchange.option_account.position]
                ),
            }
        )

    def form_curve(self):
        """
        生成资金曲线
        :return:
        """
        equity_curve = pd.DataFrame(self.equity_curve)
        equity_curve.set_index('date', inplace=True)
        for col in equity_curve.columns:
            equity_curve[col] /= equity_curve[col].iat[0]
        print(equity_curve)
        equity_path = get_abs_path_from_data('%s.csv' % self.fig_name)
        equity_curve.to_csv(equity_path)
        if self.if_draw_pic:
            self.draw_pic(df=equity_curve)

    def draw_pic(self, df):
        """
        绘制资金曲线
        :param df:
        :return:
        """
        fig, ax = plt.subplots(figsize=(7, 7))
        base = ax.plot(df['base'], color='red')
        eq = ax.plot(df['equity'], color='blue')
        plt.legend(base + eq, [self.local_exchange.stock_data_fetcher.base, 'eq'])
        # stk = ax.plot(df['stock'], color='orange')
        # opt = ax.plot(df['option'], color='black')
        # plt.legend(base + eq + stk + opt, ['base', 'eq', 'stk', 'opt'])

        fig_path = get_abs_path_from_data('fig')
        plt.title(self.fig_name)
        plt.savefig(r'%s\%s.png' % (fig_path, self.fig_name))
        # plt.show()

    def back_test_main(self):
        """
        回测主体
        :return:
        """
        while not self.earth_calender.end_of_test():
            print('\n')
            print(self.earth_calender.now, '===BEGIN')

            # 如果今天是交易日
            if self.local_exchange.trading_calender.tradable_date(
                date=self.earth_calender.now
            ):
                stock_sig = self.generate_stock_strategy_signal()  # 股票策略信号
                option_sig = self.generate_option_strategy_signal()  # 期权策略信号
                # 股票调仓
                stock_res = self.change_stock_position(
                    stock_sig=stock_sig
                )
                if stock_res:
                    #  期权调仓
                    self.change_option_position(
                        option_sig=option_sig
                    )
                else:
                    print('有开盘涨跌停，不调仓')

            self.append_equity()
            self.earth_calender.next_day()

        self.form_curve()

    def generate_stock_strategy_signal(self):
        """
        生成股票信号
        :return:
        """
        return NotImplementedError

    def generate_option_strategy_signal(self):
        """
        生成期权信号
        :return:
        """
        return NotImplementedError

    def change_stock_position(self, stock_sig):
        """
        股票账户调仓
        :param stock_sig:
        :return:
        """
        return NotImplementedError

    def change_option_position(self, option_sig):
        """
        期权账户调仓
        :param option_sig:
        :return:
        """
        return NotImplementedError

    def account_balance(self):
        """
        在股票和期权账户之间重置仓位。按照初始设定的比例划转资金。
        如果不进行的话，对冲类策略有可能在一个账户里积累大量的现金，另一个账户亏穿
        一般在移仓换月的时候进行，即平仓-平衡账户-开仓，此时股票账户必须跟着平一次仓
        :return:
        """
        # 股票账户进行平仓
        for pos in self.local_exchange.stock_account.position:
            self.local_exchange.close_order(
                market='stock',
                symbol=pos['symbol'],
                price=self.local_exchange.stock_data_fetcher.get_symbol_field(
                    symbol=pos['symbol'],
                    date=self.earth_calender.now,
                    field=['open']
                )['open'],
                amount=-pos['amount']
            )
        while {} in self.local_exchange.stock_account.position:
            self.local_exchange.stock_account.position.remove({})

        now_total_cash = self.local_exchange.stock_account.cash + self.local_exchange.option_account.cash

        # 资金重置
        self.local_exchange.stock_account.cash = now_total_cash * self.stock_prop
        self.local_exchange.option_account.cash = now_total_cash * (1 - self.stock_prop)

        # 股票重新开仓
        self.change_stock_position(stock_sig=['PUREOPEN'])
