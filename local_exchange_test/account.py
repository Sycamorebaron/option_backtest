
class Account:
    def __init__(self, init_cash):
        """
        position:
        {
            'open_date': date,
            'symbol': symbol,
            'open_price': price,
            'amount': amount,
            'pnl': 0
        }
        :param init_cash:
        """
        self.cash = init_cash  # 上一次平仓后账户里的现金，不包含当前的浮动盈亏。股票交易也使保证金交易的方法来记录。
        self.position = []

    def __repr__(self):
        return 'CASH: {0}\nPOSITION:{1}'.format(
            self.cash, self.position
        )

    def equity(self, now_price, contract_num=1):
        """
        使用传入的价格计算当前账户权益
        :param now_price:
        :return:
        """
        cash = self.cash
        if self.position != []:
            for pos in self.position:
                cash += pos['amount'] * (now_price[pos['symbol']] - pos['open_price']) * contract_num
        return cash

    def stock_equity(self, now_price):
        """
        使用传入的价格计算持有股票的权益
        :param now_price:
        :return:
        """
        eq = 0
        if self.position != []:
            for pos in self.position:
                eq += pos['amount'] * now_price[pos['symbol']]
        return eq

