
from datetime import date, timedelta
from collections import Counter

from tw_market_calendar_v3 import check_market_trading_day_v3


TWSE_CSV_PATH = r"D:\USER\Downloads\holidaySchedule_115.csv"
TEST_YEAR = 2026


def run_calendar_consistency_test():
    start_date = date(TEST_YEAR, 1, 1)
    end_date = date(TEST_YEAR, 12, 31)

    current_date = start_date

    twse_counts = Counter()
    tpex_counts = Counter()

    differences = []
    unknown_dates = []
    basis_counts = {
        "TWSE": Counter(),
        "TPEx": Counter(),
    }

    total_days = 0

    while current_date <= end_date:
        date_str = current_date.isoformat()
        total_days += 1

        twse = check_market_trading_day_v3(
            "TWSE", date_str, TWSE_CSV_PATH
        )

        tpex = check_market_trading_day_v3(
            "TPEx", date_str
        )

        twse_counts[twse["status"]] += 1
        tpex_counts[tpex["status"]] += 1

        basis_counts["TWSE"][twse["basis"]] += 1
        basis_counts["TPEx"][tpex["basis"]] += 1

        if (
            twse["is_trading_day"] is None
            or tpex["is_trading_day"] is None
        ):
            unknown_dates.append({
                "date": date_str,
                "TWSE": twse,
                "TPEx": tpex,
            })

        elif (
            twse["is_trading_day"]
            != tpex["is_trading_day"]
        ):
            differences.append({
                "date": date_str,
                "TWSE": twse["status"],
                "TPEx": tpex["status"],
                "TWSE_basis": twse["basis"],
                "TPEx_basis": tpex["basis"],
            })

        current_date += timedelta(days=1)

    print("=" * 55)
    print("2026年 TWSE＋TPEx 全年交易日曆一致性測試")
    print("=" * 55)

    print(f"\n檢查總天數：{total_days}")

    for market, counts in [
        ("TWSE", twse_counts),
        ("TPEx", tpex_counts),
    ]:
        print(f"\n【{market}】")
        print(f"交易日：{counts['交易日']}")
        print(f"休市日：{counts['休市日']}")
        print(f"無法判斷：{counts['無法判斷']}")

        print("判斷依據統計：")
        for basis, count in sorted(
            basis_counts[market].items()
        ):
            print(f"  {basis}：{count}")

    print("\n" + "=" * 55)
    print(f"市場交易狀態差異：{len(differences)} 天")
    print(f"無法判斷日期：{len(unknown_dates)} 天")

    if differences:
        print("\n【交易狀態不同的日期】")
        for item in differences:
            print(
                item["date"],
                "| TWSE:", item["TWSE"],
                "| TPEx:", item["TPEx"],
                "| TWSE依據:", item["TWSE_basis"],
                "| TPEx依據:", item["TPEx_basis"],
            )

    if unknown_dates:
        print("\n【無法判斷的日期】")
        for item in unknown_dates:
            print(
                item["date"],
                "| TWSE:", item["TWSE"]["errors"],
                "| TPEx:", item["TPEx"]["errors"],
            )

    print("\n" + "=" * 55)

    if not differences and not unknown_dates:
        print("結果：全年兩市場交易狀態一致")
        print("注意：一致不代表已驗證官方資料完整性")
    else:
        print("結果：存在差異或無法判斷日期")
        print("需要進一步核對官方交易日曆")


if __name__ == "__main__":
    run_calendar_consistency_test()
