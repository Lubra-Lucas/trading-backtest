"""Sinal causal com histerese e execução exclusivamente na virada."""
import sys
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backtest'))
import tendencia_histerese as engine


def prepared(states, rows):
    df=pd.DataFrame(rows,columns=['open','high','low','close'])
    df['time']=pd.date_range('2026-09-24',periods=len(df),freq='5min',tz='UTC')
    df['state']=states
    df['atr']=10.
    return df


class Trend(unittest.TestCase):
    def simulate(self,df,**kwargs):
        return engine.simulate(df,start=df.time.iloc[0],end=df.time.iloc[-1]+pd.Timedelta(minutes=5),**kwargs)

    def test_inside_bands_keeps_state_and_requires_both_envelopes(self):
        df=pd.DataFrame({'close':[120,103,103,98,80,97],
                         'upper20':[110]*6,'upper60':[115]*6,
                         'lower20':[90]*6,'lower60':[85]*6})
        self.assertEqual(engine.hysteresis_state(df).tolist(),[1,1,1,1,-1,-1])
        df.loc[0,'close']=112
        self.assertEqual(engine.hysteresis_state(df).iloc[0],0)
        df.loc[0,'close']=87
        self.assertEqual(engine.hysteresis_state(df).iloc[0],0)

    def test_extreme_prices_do_not_close_trade_before_reversal(self):
        df=prepared([0,1,1,-1,-1],[(100,101,99,100),(100,102,98,100),(100,160,50,110),(110,112,90,95),(90,94,88,92)])
        ts=self.simulate(df,fee=0,slippage=0)
        self.assertEqual(len(ts),2)
        t=ts[0]
        self.assertEqual(t['entry_index'],2)
        self.assertEqual(t['exit_index'],4)
        self.assertEqual(t['reason'],'virada do sinal')
        self.assertAlmostEqual(t['gross_r'],-10/15)
        self.assertEqual(ts[1]['entry_index'],4)
        self.assertTrue(ts[1]['open'])

    def test_no_warmup_position_and_loss_can_exceed_one_reference_r(self):
        df=prepared([1,1,-1,-1,1,1],[(100,101,99,100),(100,101,99,100),(100,101,99,100),(100,140,95,130),(130,151,120,145),(150,151,145,148)])
        ts=self.simulate(df,fee=0,slippage=0)
        self.assertEqual(ts[0]['entry_index'],3)
        self.assertEqual(ts[0]['direction'],-1)
        self.assertAlmostEqual(ts[0]['gross_r'],-50/15)
        self.assertLess(ts[0]['gross_r'],-1)
        self.assertTrue(ts[-1]['open'])
        self.assertIsNone(ts[-1]['gross_r'])
        self.assertAlmostEqual(ts[-1]['unrealized_gross_r'],-2/15)

    def test_gross_r_independent_from_costs(self):
        df=prepared([0,1,-1,-1],[(100,101,99,100),(100,101,99,100),(100,103,99,102),(103,104,101,102)])
        a=self.simulate(df,fee=0,slippage=0)[0]
        b=self.simulate(df,fee=.0005,slippage=.0001)[0]
        self.assertEqual(a['gross_r'],b['gross_r'])
        self.assertLess(b['net_r'],a['net_r'])

    def test_sma_and_atr_no_repaint(self):
        x=100+np.sin(np.arange(400)/13)*8
        df=pd.DataFrame(dict(time=pd.date_range('2026-09-01',periods=len(x),freq='5min',tz='UTC'),open=x,high=x+1,low=x-1,close=x))
        full=engine.indicators(df)
        pd.testing.assert_frame_equal(full.iloc[:200],engine.indicators(df.iloc[:200]))
        self.assertAlmostEqual(full.sma20.iloc[100],x[81:101].mean())
        self.assertAlmostEqual(full.sma60.iloc[100],x[41:101].mean())
        self.assertAlmostEqual(full.upper20.iloc[100],full.sma20.iloc[100]+1.5*full.atr.iloc[100])
        self.assertGreater((full.state.diff().abs()==2).sum(),0)

if __name__=='__main__':unittest.main()
