"""BTCUSDT M5: EMA9/21, stop fixo 1,5 ATR Wilder(14), alvo 2R.

Execução: python backtest/cruzamento_medias.py
Não altera o laboratório legado nem usa dados artificiais no relatório real.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent
START = '2026-09-24T00:00:00Z'
END = '2026-10-01T00:00:00Z'  # exclusivo
FEE = .0005
SLIPPAGE = .0001
RULES = [
    'BTCUSDT • 5 minutos • 24 a 30/09/2026 (UTC). Aquecimento: 01 a 23/09, sem operações.',
    'EMA 9 cruza acima da EMA 21: compra; cruza abaixo: venda. Igualdade anterior conta como cruzamento. Somente candles fechados.',
    'Sinal no fechamento; ordem a mercado na abertura seguinte. EMA por ewm ajustado=False; ATR Wilder(14), iniciado pela média dos 14 primeiros True Ranges.',
    'Um único stop fixo: 1,5 × ATR do candle do sinal, medido a partir do preço executado da entrada. Não há trailing, breakeven ou parciais.',
    '1R = distância de preço entre entrada e stop. Alvo executável em 2R; 1R e 3R são referências visuais, sem ordens.',
    'Sai no stop, no alvo 2R ou na abertura seguinte ao cruzamento contrário. Uma posição por vez; pode reverter no cruzamento contrário.',
    'Após stop ou alvo, aguarda novo cruzamento. Estar acima/abaixo da média não autoriza reentrada.',
    'Taxa: 0,05% do financeiro por lado. Slippage adverso: 0,01% em cada preenchimento, inclusive alvo. R líquido desconta taxas e slippage.',
    'Gap além do stop executa na abertura, com slippage. Gap além do alvo executa conservadoramente no alvo. Se stop e alvo aparecem no mesmo candle sem resolução temporal, conta stop.',
    'Se há cruzamento contrário pendente, verifica primeiro eventual stop na abertura; depois fecha/reverte. Ordens intrabar do candle anterior já foram processadas.',
    'Operação restante ao fim é marcada em aberto, fora das estatísticas de trades fechados. Sem encerramento artificial no fim do período.',
    'Dados de preço são Binance spot. Vendas são simulações direcionais e exigiriam margem/derivativo no ao vivo. Funding, empréstimo, latência e restrições de lote não estão modelados.',
    'Não há otimização no período. Abertura seguinte é uma aproximação: no ao vivo o preenchimento real pode diferir. R somado usa risco uniforme por operação e não representa retorno percentual de uma carteira.',
]


def validate_candles(df):
    if df.empty:
        raise ValueError('Série de candles vazia')
    if not df.time.is_monotonic_increasing or df.time.duplicated().any():
        raise ValueError('Timestamps fora de ordem ou duplicados')
    if not df.time.diff().iloc[1:].eq(pd.Timedelta(minutes=5)).all():
        raise ValueError('Histórico deve ser contínuo em 5 minutos; não preencher buracos')
    if not (df.time.astype('int64') % (300 * 10**9) == 0).all():
        raise ValueError('Candles desalinhados em 5 minutos')
    prices = df[['open','high','low','close']]
    if not np.isfinite(prices).all().all() or (prices <= 0).any().any():
        raise ValueError('Preços inválidos')
    if (df.high < prices[['open','close','low']].max(axis=1)).any() or (df.low > prices[['open','close','high']].min(axis=1)).any():
        raise ValueError('OHLC incoerente')


def indicators(df):
    out = df.copy()
    for n in (9,21):
        out[f'ema{n}'] = out.close.ewm(span=n,adjust=False,min_periods=n).mean()
    tr = pd.concat([out.high-out.low,(out.high-out.close.shift()).abs(),(out.low-out.close.shift()).abs()],axis=1).max(axis=1)
    atr = np.full(len(out), np.nan)
    if len(out)>=14:
        atr[13]=tr.iloc[:14].mean()
        for i in range(14,len(out)):
            atr[i]=(atr[i-1]*13+tr.iloc[i])/14
    out['atr']=atr
    diff=out.ema9-out.ema21
    out['signal']=np.select([(diff>0)&(diff.shift()<=0),(diff<0)&(diff.shift()>=0)],[1,-1],default=0)
    return out


def simulate(df, *, start=START, end=END, fee=FEE, slippage=SLIPPAGE):
    if not 0<=fee<1 or not 0<=slippage<1:
        raise ValueError('Taxa e slippage devem estar entre zero e um')
    start,end=pd.Timestamp(start),pd.Timestamp(end)
    if start>=end:
        raise ValueError('Período inválido')
    df=df.reset_index(drop=True)
    trades=[]
    pos=None

    def close_position(index, price, reason):
        nonlocal pos
        d=pos['direction']
        executed=float(price*(1-d*slippage))
        gross=d*(executed-pos['entry'])
        fees=fee*(pos['entry']+executed)
        pos.update(exit_index=index,exit_time=df.time.iloc[index].isoformat(),exit=executed,
                   reason=reason,open=False,net_r=(gross-fees)/pos['risk'],
                   gross_r=gross/pos['risk'],fees_r=fees/pos['risk'],unrealized_r=None)
        trades.append(pos)
        pos=None

    for i in range(1,len(df)):
        row=df.iloc[i]
        if row.time<start or row.time>=end:
            continue
        prev=df.iloc[i-1]
        sig=int(prev.signal)
        # Abertura acontece antes de máxima/mínima intrabar.
        if pos:
            d=pos['direction']
            if d*(row.open-pos['stop'])<=0:
                close_position(i,row.open,'stop (gap)')
            elif d*(row.open-pos['target'])>=0:
                close_position(i,pos['target'],'alvo 2R')
        if pos and sig and sig!=pos['direction']:
            close_position(i,row.open,'cruzamento contrário')
        if pos is None and sig and np.isfinite(prev.atr) and prev.atr>0:
            entry=float(row.open*(1+sig*slippage))
            risk=float(1.5*prev.atr)
            pos=dict(id=len(trades)+1,direction=sig,signal_index=i-1,entry_index=i,
                     signal_time=prev.time.isoformat(),entry_time=row.time.isoformat(),
                     entry=entry,atr=float(prev.atr),risk=risk,stop=entry-sig*risk,
                     target=entry+sig*2*risk,level1=entry+sig*risk,level3=entry+sig*3*risk)
        if pos:
            d=pos['direction']
            stop_hit=(row.low<=pos['stop']) if d==1 else (row.high>=pos['stop'])
            target_hit=(row.high>=pos['target']) if d==1 else (row.low<=pos['target'])
            if stop_hit:
                close_position(i,min(row.open,pos['stop']) if d==1 else max(row.open,pos['stop']),'stop')
            elif target_hit:
                close_position(i,pos['target'],'alvo 2R')
    if pos:
        last=int(df.index[(df.time>=start)&(df.time<end)][-1])
        mark=float(df.close.iloc[last])
        # Não cobra taxa de saída de uma saída que não aconteceu.
        pos.update(exit_index=last,exit_time=df.time.iloc[last].isoformat(),exit=None,mark=mark,
                   reason='em aberto',open=True,net_r=None,gross_r=None,fees_r=None,
                   unrealized_r=(pos['direction']*(mark-pos['entry'])-fee*pos['entry'])/pos['risk'])
        trades.append(pos)
    return trades


def summarize(trades):
    rs=[t['net_r'] for t in trades if not t['open']]
    wins=sum(r>0 for r in rs)
    profits=sum(r for r in rs if r>0)
    losses=-sum(r for r in rs if r<0)
    curve=np.r_[0,np.cumsum(rs)]
    dd=float(np.max(np.maximum.accumulate(curve)-curve))
    return dict(closed=len(rs),open=sum(t['open'] for t in trades),wins=wins,
                win_rate=wins/len(rs) if rs else None,total_r=float(sum(rs)),
                expectancy_r=float(np.mean(rs)) if rs else None,
                profit_factor=profits/losses if losses else None,max_drawdown_r=dd)


def load_month():
    """Verifica checksum oficial mesmo quando ZIP já existe em cache."""
    name='BTCUSDT-5m-2026-09.zip'
    url=f'https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/5m/{name}'
    response=requests.get(url+'.CHECKSUM',timeout=20)
    response.raise_for_status()
    expected=response.text.split()[0].lower()
    path=ROOT/'cache'/'cruzamento_medias'/name
    if path.exists():
        raw=path.read_bytes()
    else:
        response=requests.get(url,timeout=30)
        response.raise_for_status()
        raw=response.content
    actual=hashlib.sha256(raw).hexdigest()
    if expected!=actual:
        raise ValueError(f'SHA-256 não confere em {name}; cache não será usado')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        csvs=[n for n in z.namelist() if n.endswith('.csv')]
        if len(csvs)!=1:
            raise ValueError('ZIP oficial deve conter um CSV')
        df=pd.read_csv(z.open(csvs[0]),header=None)
    ts=pd.to_numeric(df.iloc[:,0])
    if ts.max()>10**14:
        ts=ts//1000
    out=pd.DataFrame({'time':pd.to_datetime(ts,unit='ms',utc=True)})
    for k,c in enumerate(['open','high','low','close','volume'],1):
        out[c]=pd.to_numeric(df.iloc[:,k])
    validate_candles(out)
    expected_times=pd.date_range('2026-09-01','2026-10-01',freq='5min',inclusive='left',tz='UTC')
    if not out.time.reset_index(drop=True).equals(pd.Series(expected_times)):
        raise ValueError('Setembro/2026 incompleto; não executar relatório parcial')
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(raw)
    return out,dict(url=url,sha256=actual,candles=len(out),checksum_verified=True)


def render_report(payload, dest):
    template=(ROOT/'cruzamento_medias.html').read_text()
    payload=dict(payload,rules=RULES)
    encoded=json.dumps(payload,ensure_ascii=False,allow_nan=False).replace('<','\\u003c')
    result=template.replace('/*__REPORT_DATA__*/',encoded)
    dest=Path(dest)
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(result)
    return dest


def build_report(df, source):
    signals=indicators(df)
    # Verifica ausência de repaint na própria série usada no relatório.
    cut=len(signals)//2
    pd.testing.assert_frame_equal(signals.iloc[:cut],indicators(df.iloc[:cut]))
    trades=simulate(signals)
    view=signals[signals.time.between(pd.Timestamp(START)-pd.Timedelta(hours=4),pd.Timestamp(END),inclusive='left')]
    candles=[]
    for i,row in view.iterrows():
        candles.append(dict(index=int(i),time=int(row.time.timestamp()),open=float(row.open),
                            high=float(row.high),low=float(row.low),close=float(row.close),
                            ema9=float(row.ema9),ema21=float(row.ema21)))
    return dict(status='ready',generated_at=datetime.now(timezone.utc).isoformat(),
                start=START,end=END,source=source,candles=candles,trades=trades,
                summary=summarize(trades),fee=FEE,slippage=SLIPPAGE)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'saida'/'cruzamento_medias'/'index.html')
    args=parser.parse_args()
    try:
        df,source=load_month()
        report=build_report(df,source)
    except (requests.RequestException,ValueError,zipfile.BadZipFile) as exc:
        report=dict(status='blocked',message='Coleta real indisponível. O backtest ainda não foi executado com dados de mercado.',
                    error=str(exc),candles=[],trades=[],summary=None,start=START,end=END)
        render_report(report,args.output)
        args.output.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,allow_nan=False))
        print(f'BLOQUEADO: {exc}\nHTML de regras e status (sem resultados): {args.output}',file=sys.stderr)
        return 2
    render_report(report,args.output)
    args.output.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,allow_nan=False))
    print(json.dumps(report['summary'],indent=2))
    print(f'HTML: {args.output}')
    return 0


if __name__=='__main__':
    sys.exit(main())
