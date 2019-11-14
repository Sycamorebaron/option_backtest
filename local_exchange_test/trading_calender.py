from local_exchange_test.util import *


class TradingCalender:
    def __init__(self, init_index, engine):
        self._eg = engine
        self._date = self.date_stream_init(init_index)

    @property
    def date(self):
        return self._date

    def date_stream_init(self, index):
        sql = 'select * from "%s"' % index
        df = pd.read_sql_query(sql, con=self._eg)
        df['date'] = pd.to_datetime(df['date'])

        df = df[['date', 'close']].copy()
        return df

    # 检查传入的时间是否可交易
    def tradable_date(self, date):
        date = pd.to_datetime(date)
        if date in list(self._date['date'].values):
            return True
        else:
            return False

    # 根据交易日找下一个交易日
    def get_next_trading_date(self, date):
        next_date = pd.to_datetime(self._date.loc[self._date['date'].shift(1) == date, 'date'].values[0])
        return next_date

    # 根据交易日找前一个交易日
    def get_last_trading_date(self, date):
        last_date = pd.to_datetime(self._date.loc[self._date['date'].shift(-1) == date, 'date'].values[0])
        return last_date

    # 是否是本月第一个交易日
    def if_first_trading_date(self, date):
        if not self.tradable_date(date):
            return False
        else:
            last_trading_date = self.get_last_trading_date(date)
            if date.month != last_trading_date.month:
                return True
            else:
                return False

    # 找某个月第一个交易日
    def get_monthly_first_trading_date(self, month):
        """
        :param month: '2019-01'
        :return:
        """
        now_earth_date = pd.to_datetime(month + '-01')
        while not self.tradable_date(now_earth_date):
            now_earth_date += timedelta(days=1)
        return now_earth_date.strftime('%Y-%m-%d')

    def month_remain_trading_date(self, date):
        """
        当月还有几个交易日（含当日）
        :param date:
        :return:
        """
        _date = self._date.copy()
        _date['yr_m'] = _date['date'].apply(lambda x: x.strftime('%Y-%m'))
        tar_month = _date.loc[_date['yr_m'] == date.strftime('%Y-%m')]
        return timedelta(days=len(tar_month.loc[tar_month['date'] >= date]))

if __name__ == '__main__':
    trading_calender = TradingCalender(engine=stk_eg, init_index='sh000001')
    res_days = trading_calender.month_remain_trading_date(date=pd.to_datetime('2019-10-01'))
    print(res_days)
