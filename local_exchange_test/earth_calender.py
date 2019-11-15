from local_exchange_test.util import *

"""
逐日推进的日历，用于控制时间，回测开始以及回测结束。
"""
class EarthCalender:
    def __init__(self, begin, end):
        self._begin = begin
        self._end = end
        self._now = self._begin

    @property
    def begin(self):
        return self._begin

    @property
    def end(self):
        return self._end

    @property
    def now(self):
        return self._now

    def next_day(self):
        self._now += timedelta(days=1)
        return self._now

    def end_of_test(self):
        if self._now <= self._end:
            return False
        else:
            return True

    def month_remain_date(self, date):
        """
        当月还有几天，含当日
        :param date:
        :return:
        """
        if int(date.strftime('%m')) < 12:
            next_month_first_date = '{0}-{1}-01'.format(date.strftime('%Y'), int(date.strftime('%m')) + 1)
        else:
            next_month_first_date = '{0}-{1}-01'.format(int(date.strftime('%Y')) + 1, 1)
        return pd.to_datetime(next_month_first_date) - timedelta(days=1) - date + timedelta(days=1)


if __name__ == '__main__':

    earth_cal = EarthCalender(begin=pd.to_datetime('2019-01-01'), end=pd.to_datetime('2019-10-01'))
    print(earth_cal.month_remain_date(date=pd.to_datetime('2019-08-31')))
