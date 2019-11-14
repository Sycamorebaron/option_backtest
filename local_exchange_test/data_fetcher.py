from local_exchange_test.util import *


class DataFetcher:
    def __init__(self, engine, base, schema, label):
        self._engine = engine
        self._base = base
        self._schema = schema
        self._base_data = self._get_base_data(table=self._base)
        self.label = label

    @property
    def base(self):
        return self._base

    def _get_base_data(self, table):
        """
        获取50ETF数据，直接存在内存
        :return:
        """
        sql = 'select * from "%s"' % table
        data = pd.read_sql_query(sql, con=self._engine)
        data['date'] = pd.to_datetime(data['date'])
        data = data[['date', 'open', 'high', 'low', 'close', 'volume', 'amount']].copy()
        data.sort_values(by='date', inplace=True)
        data.reset_index(drop=True, inplace=True)
        return data

    def get_base_data(self, date, limit):
        """
        获取50etf的数据，用于判断实值虚值
        :param date: datetime
        :param limit:
        :return:
        """
        d = self._base_data.loc[self._base_data['date'] <= date].copy()
        d = d[-limit:-1].copy()
        d.reset_index(drop=True, inplace=True)

        return d

    def get_option_trading_data(self, date):
        """
        获取当天的期权收盘价数据
        :param date: datetime
        :return:
        """
        sql = 'select * from "%s"."%s"' % (self._schema, date.strftime('%Y-%m-%d'))
        data = pd.read_sql_query(sql, con=self._engine)
        return data

    def get_base_price(self, date, field):
        """
        获取当天的50etf字段
        :param date: datetime
        :param field:
        :return:
        """

        return self._base_data.loc[self._base_data['date'] == date, field].values[0]

    def get_symbol_field(self, symbol, date, field):
        """
        获取给定期权某一天的某些字段的数据
        :param symbol: str
        :param date: datetime
        :param field: list
        :return:
        """
        res = {}
        data = self.get_option_trading_data(date=date)
        try:
            for f in field:
                res[f] = data.loc[data[self.label] == symbol, f].values[0]
        except Exception as e:
            print(e)
            print(data)
            print(date, symbol, field)
            raise e

        return res

    def get_all_symbol_field(self, date, field):
        """
        获取某一天所有期权某字段的值
        :param date:
        :param field:
        :return:
        """
        data = self.get_option_trading_data(date=date)
        data = data[[self.label, field[0]]].copy()
        res = {}
        for i in range(len(data)):
            res[data[self.label].iat[i]] = data[field[0]].iat[i]

        return res
