from local_exchange_test.util import *
from local_exchange_test.agent import Agent


class CollarStockAgent(Agent):
    """
    示例：领口策略
    等权买入target_stk中的十只股票，月度rebalance
    同时买入当月虚一档认沽，卖出当月虚二档认购，到期前5天进行移仓换月
    当50ETF除息时，将持有的非标准期权平仓，重新开标准合约

    """

    def __init__(self, cash, begin, end, if_draw_pic, stock_prop, fig_name, check_individual_account):
        Agent.__init__(self, cash, begin, end, if_draw_pic, stock_prop, fig_name, check_individual_account)
        self.target_stk = [
            '600036.SH', '600030.SH', '601318.SH', '600519.SH', '600585.SH',
            '000333.SZ', '600276.SH', '600104.SH', '600009.SH', '600887.SH'
        ]

    def openable(self, target_stk):
        openable = True
        for stk in target_stk:
            try:
                openable = openable & self.local_exchange.stock_market.if_tradable(
                    date=self.earth_calender.now,
                    symbol=stk,
                    buy_or_sell='buy'
                )
            except Exception as e:
                print(e)
                raise e

        return openable

    def generate_stock_strategy_signal(self):
        """
        计算股票的信号
        :return:
        """
        # 初始开仓
        if not self.local_exchange.stock_account.position:
            return ['PUREOPEN']

        # 月度rebalance
        elif (self.earth_calender.month_remain_date(date=self.earth_calender.now) <= timedelta(days=5)) and \
                not self.monthly_rebalanced:
            self.monthly_rebalanced = True
            return ['REBALANCE']

        # 无信号
        else:
            return []

    def generate_option_strategy_signal(self):
        """
        计算期权的信号
        :return:
        """
        # 初始开仓
        if not self.local_exchange.option_account.position:
            return ['PUREOPEN']

        # 移仓换月
        elif self.local_exchange.option_market.to_expire_date(
            symbol=self.local_exchange.option_account.position[0]['symbol'],
            date=self.earth_calender.now
        ) <= timedelta(days=5):
            return ['PROLONG']

        # 换标准券
        elif self.local_exchange.option_data_fetcher.get_symbol_field(
            symbol=self.local_exchange.option_account.position[0]['symbol'],
            date=self.earth_calender.now,
            field=['contract_num']
        )['contract_num'] != 10000:
            return ['CHANGESTD']

        # 无信号
        else:
            return []

    def change_stock_position(self, stock_sig):
        """
        进行股票的调仓，返回是否调仓成功
        先看是不是首次开仓，再看是不是需要rebalance
        :param stock_sig:
        :return: True or False
        """

        # 纯开仓
        if 'PUREOPEN' in stock_sig:
            now_cash = self.local_exchange.stock_account.cash

            if not self.openable(target_stk=self.target_stk):
                return False

            for stk in self.target_stk:
                open_amount = self.local_exchange.stock_market.cal_open_amount(
                    date=self.earth_calender.now,
                    symbol=stk,
                    money=now_cash / len(self.target_stk),
                    fee=self.local_exchange.stock_fee
                )
                self.local_exchange.open_order(
                    market='stock',
                    symbol=stk,
                    price=self.local_exchange.stock_data_fetcher.get_symbol_field(
                        symbol=stk,
                        date=self.earth_calender.now,
                        field=['open']
                    )['open'],
                    amount=open_amount,
                    date=self.earth_calender.now,
                    check_cash=self.check_individual_account
                )
            print('STOCK INIT OPEN')

        # rebalance
        if 'REBALANCE' in stock_sig:
            # 先用当天开盘价计算总权益
            stk_price = self._get_price(field='open', market='stock')

            # rebalance时需要使用账户里全部的钱
            stock_equity = self.local_exchange.stock_account.equity(now_price=stk_price)
            if not self.openable(target_stk=self.target_stk):
                return False

            # 逐股计算应开股数，并调仓
            for stk in self.target_stk:
                should_open_amount = self.local_exchange.stock_market.cal_open_amount(
                    date=self.earth_calender.now,
                    symbol=stk,
                    money=stock_equity / len(self.target_stk),
                    fee=self.local_exchange.stock_fee
                )
                if should_open_amount < 0:
                    print(stock_equity)
                    print(self.local_exchange.stock_account)
                    raise Exception('NEGATIVE SHOULD OPEN AMOUNT')
                for i in range(len(self.local_exchange.stock_account.position)):
                    pos = self.local_exchange.stock_account.position[i]
                    if pos['symbol'] == stk:
                        # 补仓
                        if should_open_amount > pos['amount']:
                            self.local_exchange.open_order(
                                market='stock',
                                symbol=pos['symbol'],
                                price=stk_price[pos['symbol']],
                                amount=should_open_amount - pos['amount'],
                                date=self.earth_calender.now,
                                check_cash=self.check_individual_account
                            )
                        # 减仓
                        elif should_open_amount < pos['amount']:
                            self.local_exchange.close_order(
                                market='stock',
                                symbol=pos['symbol'],
                                price=stk_price[pos['symbol']],
                                amount=should_open_amount - pos['amount'],
                            )
                        break

        return True

    def change_option_position(self, option_sig):
        """
        先看是不是首次开仓，在看是不是要移仓换月，最后看是不是要换标准券
        :param option_sig:
        :return:
        """
        _open, _close, _contract_num, _today_open, _account_reset = False, False, 10000, False, False

        # 首次开仓
        if 'PUREOPEN' in option_sig:
            _close = False
            _open = True
            print('OPTION INIT OPEN')

        # 移仓换月
        if 'PROLONG' in option_sig:
            _close = True
            _open = True
            _account_reset = True
            print('OPTION PROLONG')

        # 换到标准券，平仓需查看当前合约单位
        if 'CHANGESTD' in option_sig:
            _close = True
            _open = True
            _contract_num = self.local_exchange.option_data_fetcher.get_symbol_field(
                symbol=self.local_exchange.option_account.position[0]['symbol'],
                date=self.earth_calender.now,
                field=['contract_num']
            )['contract_num']
            _today_open = True
            print('OPTION CHANGE TO STD')

        # 需要平仓
        if _close:
            for pos in self.local_exchange.option_account.position:
                self.local_exchange.close_order(
                    market='option',
                    symbol=pos['symbol'],
                    price=self.local_exchange.option_data_fetcher.get_symbol_field(
                        symbol=pos['symbol'],
                        date=self.earth_calender.now,
                        field=['open']
                    )['open'],
                    amount=-pos['amount'],
                    contract_num=_contract_num
                )
            while {} in self.local_exchange.option_account.position:
                self.local_exchange.option_account.position.remove({})

        # 重置账户
        if _account_reset & self.check_individual_account:
            self.account_balance()

        # 需要开仓
        if _open:
            if _today_open:
                base_price = self.local_exchange.option_data_fetcher.get_base_price(
                    date=self.earth_calender.now,
                    field='open'
                )
            else:
                base_price = self.local_exchange.option_data_fetcher.get_base_price(
                    date=self.local_exchange.trading_calender.get_last_trading_date(
                        date=self.earth_calender.now
                    ),
                    field='close'
                )
            # 选择距离到期大于5天的当月/次月虚一档认沽
            target_put = self.local_exchange.option_market.get_target_option(
                target_side='put',
                inner=-1,
                base_price=base_price,
                date=self.earth_calender.now,
                expire_limit=5
            )
            # 选择距离到期大于5天的当月/次月虚二档认购
            target_call = self.local_exchange.option_market.get_target_option(
                target_side='call',
                inner=-2,
                base_price=base_price,
                date=self.earth_calender.now,
                expire_limit=5
            )
            # 根据当前股票市值，决定开仓张数
            stk_price = self._get_price(field='open', market='stock')

            # 计算期权应对冲仓位时使用持有股票的市值
            stock_equity = self.local_exchange.stock_account.stock_equity(now_price=stk_price)
            open_amount = int(stock_equity / (10000 * base_price))

            # LONG PUT
            self.local_exchange.open_order(
                market='option',
                symbol=target_put,
                price=self.local_exchange.option_data_fetcher.get_symbol_field(
                    symbol=target_put,
                    date=self.earth_calender.now,
                    field=['open']
                )['open'],
                amount=open_amount,
                date=self.earth_calender.now,
                check_cash=self.check_individual_account
            )

            # SHORT CALL
            self.local_exchange.open_order(
                market='option',
                symbol=target_call,
                price=self.local_exchange.option_data_fetcher.get_symbol_field(
                    symbol=target_call,
                    date=self.earth_calender.now,
                    field=['open']
                )['open'],
                amount=-open_amount,
                date=self.earth_calender.now,
                check_cash=self.check_individual_account
            )

    def _get_price(self, market, field):
        if market == 'stock':
            stk_price = {}
            for stk in self.target_stk:
                stk_price[stk] = self.local_exchange.stock_data_fetcher.get_symbol_field(
                    symbol=stk,
                    date=self.earth_calender.now,
                    field=[field]
                )[field]
            return stk_price
        else:
            option_price = {}
            for pos in self.local_exchange.option_account.position:
                option_price[pos['symbol']] = self.local_exchange.option_data_fetcher.get_symbol_field(
                    symbol=pos['symbol'],
                    date=self.earth_calender.now,
                    field=[field]
                )[field]
            return option_price

    def option_stock_balance(self):
        """
        保持期权对股票的对冲
        :return:
        """
        base_price = self.local_exchange.option_data_fetcher.get_base_price(
            date=self.earth_calender.now,
            field='open'
        )

        # 根据当前股票市值，决定开仓张数
        stk_price = self._get_price(field='open', market='stock')
        stock_equity = self.local_exchange.stock_account.stock_equity(now_price=stk_price)
        should_open_amount = int(stock_equity / (10000 * base_price))

        if self.local_exchange.option_account.position:
            for pos in self.local_exchange.option_account.position:
                # 如果abs(应开)-abs(已开)>0，则需要补仓
                if abs(should_open_amount) > abs(pos['amount']):
                    print('补仓%s' %
                          ((abs(should_open_amount) - abs(pos['amount']))*(pos['amount'] / abs(pos['amount']))))
                    self.local_exchange.open_order(
                        market='option',
                        symbol=pos['symbol'],
                        price=self.local_exchange.option_data_fetcher.get_symbol_field(
                            symbol=pos['symbol'],
                            date=self.earth_calender.now,
                            field=['open']
                        )['open'],
                        amount=(abs(should_open_amount) - abs(pos['amount']))*(pos['amount'] / abs(pos['amount'])),
                        date=self.earth_calender.now,
                        check_cash=self.check_individual_account
                    )

                # 如果abs(应开)-abs(已开)<0，则需要减仓
                elif abs(should_open_amount) < abs(pos['amount']):
                    print('减仓%s' %
                          ((abs(pos['amount']) - abs(should_open_amount)) * (-pos['amount'] / abs(pos['amount']))))
                    self.local_exchange.close_order(
                        market='option',
                        symbol=pos['symbol'],
                        price=self.local_exchange.option_data_fetcher.get_symbol_field(
                            symbol=pos['symbol'],
                            date=self.earth_calender.now,
                            field=['open']
                        )['open'],
                        amount=(abs(pos['amount']) - abs(should_open_amount)) * (-pos['amount'] / abs(pos['amount']))
                    )

    def back_test_main(self):
        while not self.earth_calender.end_of_test():
            print('\n')
            print(self.earth_calender.now, '===BEGIN')

            # 如果今天是交易日
            if self.local_exchange.trading_calender.tradable_date(
                date=self.earth_calender.now
            ):
                stock_sig = self.generate_stock_strategy_signal()  # 股票策略信号
                option_sig = self.generate_option_strategy_signal()  # 期权策略信号
                print(stock_sig, option_sig)
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

                self.option_stock_balance()

                self.append_equity()

                option_price = agent._get_price(field='close', market='option')
                print('OPTION ACCOUNT EQUITY',
                      self.local_exchange.option_account.equity(now_price=option_price, contract_num=10000))
                stock_price = agent._get_price(field='close', market='stock')
                print('STOCK ACCOUNT EQUITY', self.local_exchange.stock_account.equity(now_price=stock_price))

                sum_eq = self.local_exchange.equity(date=self.earth_calender.now)
                print('NOW SUM EQUITY', sum_eq)

                # 本月已更新状态同步
                if self.earth_calender.now.strftime('%m') != self.local_exchange.trading_calender.get_last_trading_date(
                        date=self.earth_calender.now).strftime('%m'):
                    self.monthly_rebalanced = False

                # 检查账户是否为负数
                if self.check_individual_account:
                    if self.local_exchange.option_account.cash < 0:
                        raise Exception('OPTION ACCOUNT CASH < 0')
                    elif self.local_exchange.stock_account.cash < 0:
                        raise Exception('STOCK ACCOUNT CASH < 0')

            print(self.earth_calender.now, '===END\n')
            self.earth_calender.next_day()

        self.form_curve()


if __name__ == '__main__':

    agent = CollarStockAgent(
        cash=10000000,
        begin=pd.to_datetime('2015-02-10'),
        end=pd.to_datetime('2019-10-31'),
        if_draw_pic=True,
        stock_prop=0.6,
        fig_name='LSOS',
        check_individual_account=False
    )

    agent.back_test_main()
