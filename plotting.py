import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import json
from pure_funcs import round_dynamic, denumpyize, candidate_to_live_config
from njit_funcs import round_up
from procedures import dump_live_config


def dump_plots(result: dict, fdf: pd.DataFrame, df: pd.DataFrame):
    plt.rcParams['figure.figsize'] = [29, 18]
    pd.set_option('precision', 10)

    def gain_conv(x):
        return x * 100 - 100

    lines = []
    lines.append(f"exchange {result['exchange'] if 'exchange' in result else 'unknown'}")
    lines.append(f"symbol {result['symbol'] if 'symbol' in result else 'unknown'}")
    lines.append(f"gain percentage {round_dynamic(result['result']['gain'] * 100 - 100, 4)}%")
    lines.append(f"average_daily_gain percentage {round_dynamic((result['result']['average_daily_gain'] - 1) * 100, 3)}%")
    lines.append(f"closest_bkr percentage {round_dynamic(result['result']['closest_bkr'] * 100, 4)}%")
    lines.append(f"starting balance {round_dynamic(result['starting_balance'], 3)}")

    for key in [k for k in result['result'] if k not in ['gain', 'average_daily_gain', 'closest_bkr', 'do_long', 'do_shrt']]:
        lines.append(f"{key} {round_dynamic(result['result'][key], 6)}")
    lines.append(f"long: {result['do_long']}, short: {result['do_shrt']}")

    longs = fdf[fdf.type.str.contains('long')]
    shrts = fdf[fdf.type.str.contains('shrt')]

    lines.append(f"n long ientries {len(longs[longs.type == 'long_ientry'])}")
    lines.append(f"n long rentries {len(longs[longs.type == 'long_rentry'])}")
    lines.append(f"n long ncloses {len(longs[longs.type == 'long_nclose'])}")
    lines.append(f"n long scloses {len(longs[longs.type == 'long_sclose'])}")
    lines.append(f"long pnl sum {longs.pnl.sum()}")

    lines.append(f"n shrt ientries {len(shrts[shrts.type == 'shrt_ientry'])}")
    lines.append(f"n shrt rentries {len(shrts[shrts.type == 'shrt_rentry'])}")
    lines.append(f"n shrt ncloses {len(shrts[shrts.type == 'shrt_nclose'])}")
    lines.append(f"n shrt scloses {len(shrts[shrts.type == 'shrt_sclose'])}")
    lines.append(f"shrt pnl sum {shrts.pnl.sum()}")


    live_config = candidate_to_live_config(result)
    dump_live_config(live_config, result['plots_dirpath'] + 'live_config.json')
    json.dump(denumpyize(result), open(result['plots_dirpath'] + 'result.json', 'w'), indent=4)

    print('writing backtest_result.txt...')
    with open(f"{result['plots_dirpath']}backtest_result.txt", 'w') as f:
        for line in lines:
            print(line)
            f.write(line + '\n')

    print('plotting balance and equity...')
    plt.clf()
    fdf.balance.plot()
    fdf.equity.plot()
    plt.savefig(f"{result['plots_dirpath']}balance_and_equity.png")


    plt.clf()
    longs.pnl.cumsum().plot()
    plt.savefig(f"{result['plots_dirpath']}pnl_cumsum_long.png")

    plt.clf()
    shrts.pnl.cumsum().plot()
    plt.savefig(f"{result['plots_dirpath']}pnl_cumsum_shrt.png")

    plt.clf()
    fdf.adg.plot()
    plt.savefig(f"{result['plots_dirpath']}adg.png")

    print('plotting backtest whole and in chunks...')
    n_parts = max(3, int(round_up(result['n_days'] / 14, 1.0)))
    for z in range(n_parts):
        start_ = z / n_parts
        end_ = (z + 1) / n_parts
        print(f'{z} of {n_parts} {start_ * 100:.2f}% to {end_ * 100:.2f}%')
        fig = plot_fills(df, fdf.iloc[int(len(fdf) * start_):int(len(fdf) * end_)], bkr_thr=0.1)
        fig.savefig(f"{result['plots_dirpath']}backtest_{z + 1}of{n_parts}.png")
    fig = plot_fills(df, fdf, bkr_thr=0.1)
    fig.savefig(f"{result['plots_dirpath']}whole_backtest.png")

    print('plotting pos sizes...')
    plt.clf()
    longs.psize.plot()
    shrts.psize.plot()
    plt.savefig(f"{result['plots_dirpath']}psizes_plot.png")


def plot_fills(df, fdf_, side: int = 0, bkr_thr=0.1):
    plt.clf()
    fdf = fdf_.set_index('timestamp')
    dfc = df.iloc[::max(1, int(len(df) * 0.00001))]
    dfc = dfc[(dfc.timestamp > fdf.index[0]) & (dfc.timestamp < fdf.index[-1])].set_index('timestamp')
    dfc = dfc.loc[fdf.index[0]:fdf.index[-1]]
    dfc.price.plot(style='y-')

    if side >= 0:
        longs = fdf[fdf.type.str.contains('long')]
        lnentry = longs[(longs.type == 'long_ientry') | (longs.type == 'long_rentry')]
        lhentry = longs[longs.type == 'long_hentry']
        lnclose = longs[longs.type == 'long_nclose']
        lsclose = longs[longs.type == 'long_sclose']
        lnentry.price.plot(style='b.')
        lhentry.price.plot(style='bx')
        lnclose.price.plot(style='r.')
        lsclose.price.plot(style=('rx'))
        longs.where(longs.pprice != 0.0).pprice.fillna(method='ffill').plot(style='b--')
    if side <= 0:
        shrts = fdf[fdf.type.str.contains('shrt')]
        snentry = shrts[(shrts.type == 'shrt_ientry') | (shrts.type == 'shrt_rentry')]
        shentry = shrts[shrts.type == 'shrt_hentry']
        snclose = shrts[shrts.type == 'shrt_nclose']
        ssclose = shrts[shrts.type == 'shrt_sclose']
        snentry.price.plot(style='r.')
        shentry.price.plot(style='rx')
        snclose.price.plot(style='b.')
        ssclose.price.plot(style=('bx'))
        shrts.where(shrts.pprice != 0.0).pprice.fillna(method='ffill').plot(style='r--')

    if 'bkr_price' in fdf.columns:
        fdf.bkr_price.where(fdf.bkr_diff < bkr_thr, np.nan).plot(style='k--')
    return plt

