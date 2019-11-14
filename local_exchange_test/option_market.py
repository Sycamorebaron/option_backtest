from local_exchange_test.util import *

class OptionMarket:
    def __init__(self, data_fetcher, trading_calender):
        self.data_fetcher = data_fetcher
        self.trading_calender = trading_calender


    def cal_contract_margin(self, option_code, base_price, date):
        """
        计算某个期权的开仓保证金
        :param option_code:
        :return:
        """

        # {'trade_code': '510050C1512M03200', 'pre_clr': 0.3507, 'close': 0.3363,
        # 'contract_num': 10000.0, 'exer_price': 3.2}
        option_data = self.data_fetcher.get_option_field(
            option_code=option_code,
            date=date,
            field=['trade_code', 'pre_clr', 'contract_num', 'exer_price']
        )
        if option_data['contract_num'] != 10000:
            raise Exception('AGENT LINE 134')

        print('计算开仓时的指数价格{0}\n计算开仓时的前一个交易日{1}\n计算开仓的交易日{2}'.format(
            base_price,
            self.trading_calender.get_last_trading_date(date=date),
            date
        ))

        if 'P' in option_data['trade_code']:
            out_range = base_price - option_data['exer_price']  # 用前收计算期权的虚值
            if out_range < 0:

                raise Exception('OUT RANGE ERROR')
            contract_margin = min(option_data['pre_clr'] +
                                  max(0.12 * base_price - out_range,
                                      0.07 * option_data['exer_price']),
                                  option_data['exer_price']) * option_data['contract_num']

        elif 'C' in option_data['trade_code']:
            out_range = option_data['exer_price'] - base_price  # 用前收今开计算期权的虚值
            if out_range < 0:
                raise Exception('OUT RANGE ERROR')
            contract_margin = (option_data['pre_clr'] +
                               max(0.12 * base_price - out_range,
                                   0.07 * base_price)) * option_data['contract_num']
        else:
            raise Exception('Invalid trade code!')

        return contract_margin

    def _rid_unstd(self, option_info):
        """
        去掉非标准合约
        :param option_info:
        :return:
        """
        option_info = option_info.loc[option_info['contract_num'] == 10000].copy()
        option_info.reset_index(drop=True, inplace=True)

        return option_info

    def get_target_option(self, target_side, inner, base_price, date, expire_limit):
        """
        获取目标期权
        筛选当月
        2：实二档；1：实一档；0：平值；-1：虚一档；-2：虚二挡
        :param target_pos:
        :param inner:
        :param base_price:
        :param date:
        :param expire_limit: 距离到期还有几天直接去掉
        :return:
        """
        option_info = self.data_fetcher.get_option_trading_data(date=date)
        option_info = self._rid_unstd(option_info=option_info)

        print('选择日期{0}\n前一个交易日{1}\n筛选时使用的前收/今开{2}\n'.format(
            date,
            self.trading_calender.get_last_trading_date(date=date),
            base_price
        ))

        option_info.sort_values('exer_price', ascending=True, inplace=True)

        # 找到当月期权
        earliest_exer_date = option_info['exer_date'].min()
        _ch = option_info.loc[option_info['exer_date'] == earliest_exer_date]

        # 距离当月期权到期超过5天
        if earliest_exer_date - date > timedelta(days=expire_limit):
            option_info = option_info.loc[option_info['exer_date'] == earliest_exer_date]
        # 距离当月期权到期不足5天
        else:
            option_info = option_info.loc[option_info['exer_date'] > earliest_exer_date].copy()
            earliest_exer_date = option_info['exer_date'].min()
            option_info = option_info.loc[option_info['exer_date'] == earliest_exer_date]

        # 找到平值期权的行权价
        at_price = 0
        at_price_gap = 10
        for exer_price in list(option_info['exer_price']):
            if abs(exer_price - base_price) < at_price_gap:
                at_price = exer_price
                at_price_gap = abs(exer_price - base_price)

        # 找到虚值三档
        if target_side == 'call':  # 购
            target_side_option = option_info.loc[option_info['trade_code'].apply(lambda x: 'C' in x)]

            target_side_option = target_side_option.loc[target_side_option['exer_price'] > at_price]
            target_side_option.reset_index(drop=True, inplace=True)

            if len(target_side_option) < abs(inner):
                raise Exception('NOT ENOUGH DEPTH')

            target_option_code = target_side_option['option_code'].iloc[-inner - 1]  # -3 ==> 2

        else:
            target_side_option = option_info.loc[option_info['trade_code'].apply(lambda x: 'P' in x)]

            target_side_option = target_side_option.loc[target_side_option['exer_price'] < at_price]
            target_side_option.reset_index(drop=True, inplace=True)

            if len(target_side_option) < abs(inner):
                raise Exception('NOT ENOUGH DEPTH')

            target_option_code = target_side_option['option_code'].iloc[inner]  # -3 ==> -3

        return target_option_code

    def to_expire_date(self, symbol, date):
        """
        计算期权还有多少天到期（含今日，包括非交易日）
        :param symbol:
        :param date:
        :return:
        """
        holding_expire_date = self.data_fetcher.get_symbol_field(
            symbol=symbol,
            date=date,
            field=['expire_date']
        )['expire_date']
        return pd.to_datetime(holding_expire_date) - date + timedelta(days=1)


if __name__ == '__main__':
    from local_exchange_test.data_fetcher import DataFetcher
    from local_exchange_test.trading_calender import TradingCalender

    option_data_fetcher = DataFetcher(
            engine=option_eg,
            schema='trading_data',
            base='50etf',
            label='option_code'
    )
    trading_calender = TradingCalender(
            init_index='50etf',
            engine=option_eg
    )
    option_market = OptionMarket(
        data_fetcher=option_data_fetcher,
        trading_calender=trading_calender
    )
    res_days = option_market.to_expire_date(
        symbol='10001966',
        date=pd.to_datetime('2019-11-01')
    )
    print(res_days)
