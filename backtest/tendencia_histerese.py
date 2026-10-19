"""BTCUSDT M5: SMA20/60, envelopes 1,5 ATR simples(14), saída na virada."""
from __future__ import annotations
import argparse
import json
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import pandas as pd
import cruzamento_medias as base

ROOT=Path(__file__).resolve().parent
RULES=[
 'BTCUSDT spot, M5, de 24 a 30/09/2026 UTC. Aquecimento de 01 a 23/09, sem posições transportadas; aguardar a primeira virada dentro da janela.',
 'Médias simples SMA20 e SMA60. ATR(14) = média simples dos últimos 14 True Ranges, como a Ovelha V3 original. Cada média recebe faixas de ±1,5 ATR.',
 'Compra: fechamento estritamente acima das duas faixas superiores. Venda: fechamento estritamente abaixo das duas faixas inferiores. Dentro desses limites, mantém o último estado (histerese). Não exige cruzamento entre as médias.',
 'Decisão no fechamento; entrada na abertura do candle seguinte à mudança de estado. Uma posição por vez. Na virada oposta, fecha e reverte na mesma abertura.',
 'Saída exclusivamente na virada do sinal. Não há stop de preço, alvo fixo, trailing ou parciais. Tocar −1R, +1R, +2R ou +3R não encerra a posição.',
 'R bruto = direção × (saída de referência − entrada de referência) / (1,5 ATR do candle do sinal). A referência de 1R fica fixa durante o trade. Não desconta taxas ou slippage e não limita a perda a −1R.',
 'A linha vermelha de −1R é apenas referência de risco, sem ordem de stop. As faixas de médias se movem e definem a virada; o risco efetivo até a virada pode exceder 1R.',
 'Posição aberta ao fim: marcada ao último fechamento, sem saída artificial e fora do resultado, acerto e drawdown dos trades fechados. Resultado em aberto aparece separadamente.',
 'Auditoria líquida opcional: taxa de 0,05% por lado e slippage adverso de 0,01% por preenchimento. Esses custos não mudam sinais, níveis de referência nem R bruto.',
 'Candles spot; vendas são simulações direcionais. Funding, empréstimo e restrições de lote não estão modelados. Soma de R não equivale ao retorno percentual de uma carteira.',
 'Parâmetros fixos solicitados, sem grade ou otimização nesta semana. A causalidade dos indicadores é conferida com histórico truncado; uma semana não estabelece robustez.'
]


def hysteresis_state(df):
    trigger=pd.Series(np.nan,index=df.index)
    trigger[df.close>df[['upper20','upper60']].max(axis=1,skipna=False)]=1
    trigger[df.close<df[['lower20','lower60']].min(axis=1,skipna=False)]=-1
    return trigger.ffill().fillna(0).astype(int)


def indicators(df):
    out=df.copy()
    prev=out.close.shift()
    tr=pd.concat([out.high-out.low,(out.high-prev).abs(),(out.low-prev).abs()],axis=1).max(axis=1)
    out['atr']=tr.rolling(14).mean()
    for n in (20,60):
        out[f'sma{n}']=out.close.rolling(n).mean()
        out[f'upper{n}']=out[f'sma{n}']+1.5*out.atr
        out[f'lower{n}']=out[f'sma{n}']-1.5*out.atr
    out['state']=hysteresis_state(out)
    return out


def simulate(df,*,start=base.START,end=base.END,fee=base.FEE,slippage=base.SLIPPAGE):
    if not 0<=fee<1 or not 0<=slippage<1:raise ValueError('Custos inválidos')
    start,end=pd.Timestamp(start),pd.Timestamp(end)
    if start>=end:raise ValueError('Período inválido')
    df=df.reset_index(drop=True);trades=[];pos=None
    for i in range(1,len(df)):
        row,signal=df.iloc[i],df.iloc[i-1]
        if not start<=row.time<end or i<2:continue
        # É necessário haver uma mudança conhecida de estado no fechamento anterior.
        prior=int(df.state.iloc[i-2])
        state=int(signal.state)
        if not state or state==prior:continue
        if not np.isfinite(signal.atr) or signal.atr<=0:continue
        if pos and state!=pos['direction']:
            d=pos['direction'];ref=float(row.open);executed=ref*(1-d*slippage)
            fees=fee*(pos['entry_executed']+executed)
            pos.update(exit_index=i,exit_time=row.time.isoformat(),exit=executed,exit_reference=ref,
                       open=False,reason='virada do sinal',gross_r=d*(ref-pos['entry'])/pos['risk'],
                       net_r=(d*(executed-pos['entry_executed'])-fees)/pos['risk'],fees_r=fees/pos['risk'],unrealized_r=None,unrealized_gross_r=None)
            trades.append(pos);pos=None
        if pos is None:
            entry=float(row.open);risk=float(1.5*signal.atr)
            pos=dict(id=len(trades)+1,direction=state,signal_index=i-1,entry_index=i,
                     signal_time=signal.time.isoformat(),entry_time=row.time.isoformat(),entry=entry,
                     entry_executed=entry*(1+state*slippage),atr=float(signal.atr),risk=risk,
                     stop=entry-state*risk,target=entry+state*2*risk,level1=entry+state*risk,level3=entry+state*3*risk)
    if pos:
        last=int(df.index[(df.time>=start)&(df.time<end)][-1]);mark=float(df.close.iloc[last]);d=pos['direction']
        pos.update(exit_index=last,exit_time=df.time.iloc[last].isoformat(),exit=None,exit_reference=None,mark=mark,
                   open=True,reason='em aberto',gross_r=None,net_r=None,fees_r=None,
                   unrealized_gross_r=d*(mark-pos['entry'])/pos['risk'],
                   unrealized_r=(d*(mark-pos['entry_executed'])-fee*pos['entry_executed'])/pos['risk'])
        trades.append(pos)
    return trades


def build_report(df,source):
    base.validate_candles(df)
    signals=indicators(df)
    cut=len(df)//2
    pd.testing.assert_frame_equal(signals.iloc[:cut],indicators(df.iloc[:cut]))
    trades=simulate(signals)
    view=signals[signals.time.between(pd.Timestamp(base.START)-pd.Timedelta(hours=6),pd.Timestamp(base.END),inclusive='left')]
    candles=[]
    for i,row in view.iterrows():
        candle=dict(index=int(i),time=int(row.time.timestamp()))
        candle.update({key:float(row[key]) for key in ['open','high','low','close','sma20','sma60','atr','upper20','lower20','upper60','lower60']})
        candle['state']=int(row.state);candles.append(candle)
    return dict(status='ready',strategy='sma20_60_atr15_hysteresis',generated_at=datetime.now(timezone.utc).isoformat(),start=base.START,end=base.END,
                source=source,candles=candles,trades=trades,rules=RULES,summary=base.summarize(trades),gross_summary=base.summarize(trades,r_key='gross_r'),
                fee=base.FEE,slippage=base.SLIPPAGE,initial_state=int(signals.loc[signals.time<pd.Timestamp(base.START),'state'].iloc[-1]),
                open_gross_r=sum(t['unrealized_gross_r'] for t in trades if t['open']))


def render_report(report,dest):
    encoded=json.dumps(dict(report,rules=RULES),ensure_ascii=False,allow_nan=False).replace('<','\\u003c')
    html=(ROOT/'tendencia_histerese.html').read_text().replace('/*__CHART_LIBRARY__*/',(ROOT/'vendor/lightweight-charts-4.2.0.js').read_text()).replace('/*__REPORT_DATA__*/',encoded)
    dest=Path(dest);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(html)
    dest.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,allow_nan=False))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=ROOT.parent/'docs/tendencia-histerese/index.html');args=parser.parse_args()
    df,source=base.load_month();report=build_report(df,source);render_report(report,args.output)
    print(json.dumps({'gross_summary':report['gross_summary'],'net_summary':report['summary'],'open_gross_r':report['open_gross_r']},indent=2));print(f'HTML: {args.output}')

if __name__=='__main__':main()
