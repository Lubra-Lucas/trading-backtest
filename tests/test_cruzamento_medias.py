"""Verificam execução temporal, risco e custos, sem acesso à rede."""
import importlib
import sys
import unittest
import tempfile
import json
import contextlib
import io
from unittest.mock import patch
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backtest'))
try:
    engine = importlib.import_module('cruzamento_medias')
except ModuleNotFoundError:
    engine = None


def bars(rows, signals=None):
    df = pd.DataFrame(rows, columns=['open', 'high', 'low', 'close'])
    df['time'] = pd.date_range('2026-09-24', periods=len(df), freq='5min', tz='UTC')
    df['atr'] = 10.
    df['signal'] = signals or [0] * len(df)
    return df


class Execution(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(engine, 'Implementar módulo cruzamento_medias')

    def run_case(self, df, **kw):
        return engine.simulate(df, start=df.time.iloc[0], end=df.time.iloc[-1]+pd.Timedelta(minutes=5), **kw)

    def test_next_open_entry_and_fixed_atr(self):
        df = bars([(100,101,99,100),(110,120,105,115),(115,146,114,140)], [1,0,0])
        t = self.run_case(df, fee=0, slippage=0)[0]
        self.assertEqual(t['entry_index'],1)
        self.assertEqual(t['entry'],110)
        self.assertEqual(t['stop'],95)
        self.assertEqual(t['target'],140)
        self.assertEqual(t['reason'],'alvo 2R')
        self.assertAlmostEqual(t['net_r'],2)

    def test_stop_wins_when_both_touched(self):
        df = bars([(100,101,99,100),(100,135,80,100)], [1,0])
        t = self.run_case(df, fee=0, slippage=0)[0]
        self.assertEqual(t['reason'],'stop')
        self.assertEqual(t['net_r'],-1)

    def test_gap_beyond_stop_fills_at_open(self):
        df = bars([(100,101,99,100),(100,105,90,100),(75,90,70,80)], [1,0,0])
        t = self.run_case(df, fee=0, slippage=0)[0]
        self.assertEqual(t['exit'],75)
        self.assertLess(t['net_r'],-1)

    def test_short_target_and_both_side_fees(self):
        df = bars([(100,101,99,100),(100,105,65,80)], [-1,0])
        t = self.run_case(df, fee=.0005, slippage=0)[0]
        self.assertEqual(t['exit'],70)
        self.assertAlmostEqual(t['net_r'],(30-.0005*170)/15)

    def test_adverse_slippage_on_entry_and_exit(self):
        df = bars([(100,101,99,100),(100,135,80,100)], [1,0])
        t = self.run_case(df, fee=0, slippage=.001)[0]
        self.assertAlmostEqual(t['entry'],100.1)
        self.assertAlmostEqual(t['exit'],85.1*.999)

    def test_no_reentry_until_new_cross_and_reversal_at_next_open(self):
        df = bars([(100,101,99,100),(100,102,80,95),(95,100,90,95),(95,100,90,95),(95,100,90,95)], [1,0,-1,0,0])
        trades = self.run_case(df, fee=0, slippage=0)
        self.assertEqual([t['entry_index'] for t in trades],[1,3])
        self.assertTrue(trades[-1]['open'])

    def test_reversal_exits_at_next_open(self):
        df = bars([(100,101,99,100),(100,102,98,100),(101,104,99,102),(102,105,100,103)], [1,-1,0,0])
        trades=self.run_case(df, fee=0, slippage=0)
        self.assertEqual(trades[0]['reason'],'cruzamento contrário')
        self.assertEqual(trades[0]['exit_index'],2)
        self.assertEqual(trades[1]['entry_index'],2)

    def test_last_position_marked_open_and_no_future_fill(self):
        df=bars([(100,101,99,100),(100,103,99,102)], [1,-1])
        trades=self.run_case(df, fee=0, slippage=0)
        self.assertEqual(len(trades),1)
        self.assertTrue(trades[0]['open'])
        self.assertIsNone(trades[0]['net_r'])
        self.assertAlmostEqual(trades[0]['unrealized_r'],2/15)

    def test_indicators_causal_and_actual_crosses(self):
        x=100+np.sin(np.arange(500)/8)*10
        df=bars([(v,v+1,v-1,v) for v in x])
        full=engine.indicators(df)
        pd.testing.assert_frame_equal(full.iloc[:250],engine.indicators(df.iloc[:250]))
        self.assertGreater((full.signal!=0).sum(),10)
        self.assertTrue((full.loc[full.signal==1,'ema9']>full.loc[full.signal==1,'ema21']).all())
        expected_tr = [2.] + [max(2., abs(x[i]+1-x[i-1]), abs(x[i]-1-x[i-1])) for i in range(1,14)]
        self.assertAlmostEqual(full.atr.iloc[13],sum(expected_tr)/14)

    def test_reject_missing_candle_before_signals(self):
        df=bars([(100,101,99,100)]*20).drop(index=5)
        with self.assertRaisesRegex(ValueError,'5 minutos'):
            engine.validate_candles(df)

    def test_summary_excludes_open_positions(self):
        df=bars([(100,101,99,100),(100,135,80,100),(100,101,99,100),(100,101,99,100)],[1,0,-1,0])
        trades=self.run_case(df,fee=0,slippage=0)
        s=engine.summarize(trades)
        self.assertEqual(s['closed'],1)
        self.assertEqual(s['open'],1)
        self.assertEqual(s['total_r'],-1)


    def test_pending_report_does_not_fabricate_results(self):
        with tempfile.TemporaryDirectory() as d:
            try:
                path=engine.render_report(dict(status='blocked',candles=[],trades=[],summary=None),Path(d)/'index.html')
            except FileNotFoundError:
                self.fail('Template HTML ainda não implementado')
            html=path.read_text()
            data=json.loads(html.split('<script id="report-data" type="application/json">')[1].split('</script>')[0])
            self.assertEqual(data['status'],'blocked')
            self.assertEqual(data['trades'],[])
            self.assertIsNone(data['summary'])
            self.assertIn('1,5 × ATR',html)
            self.assertNotIn('/*__REPORT_DATA__*/',html)

    def test_report_escapes_script_in_data(self):
        with tempfile.TemporaryDirectory() as d:
            try:
                p=engine.render_report(dict(status='blocked',message='</script><script>bad()</script>'),Path(d)/'index.html')
            except FileNotFoundError:
                self.fail('Template HTML ainda não implementado')
            self.assertNotIn('</script><script>bad()',p.read_text())


    def test_failed_refresh_replaces_previous_successful_json(self):
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder)/'index.html'
            output.with_suffix('.json').write_text('{"status":"ready","trades":[{"id":1}]}')
            with patch.object(sys,'argv',['cruzamento_medias','--output',str(output)]), patch.object(engine,'load_month',side_effect=engine.requests.ConnectionError('bloqueio de teste')), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(engine.main(),2)
            data=json.loads(output.with_suffix('.json').read_text())
            self.assertEqual(data['status'],'blocked')
            self.assertEqual(data['trades'],[])


if __name__=='__main__': unittest.main()
