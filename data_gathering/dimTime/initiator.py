import pandas as pd
from pathlib import Path
import sys

from data_gathering.hulp_functies import filterNewRows

ROOT = Path().resolve().parents[1] 
sys.path.append(str(ROOT))

def dimTime():
    # Genereer tijdstippen voor 1 volledige dag per minuut
    time_range = pd.date_range("00:00", "23:59", freq="1min")
    df_time = pd.DataFrame({'fullTime': time_range.time})

    # PK format: HHMM (bijv 235900)
    df_time['TimeKey'] = [int(t.strftime('%H%M')) for t in df_time['fullTime']]
    df_time['Hour'] = [t.hour for t in df_time['fullTime']]
    df_time['Minute'] = [t.minute for t in df_time['fullTime']]
    df_time['AMPM'] = [t.strftime('%p') for t in df_time['fullTime']]
    df_time['Hour12'] = [int(t.strftime('%I')) for t in df_time['fullTime']]

    df_time = filterNewRows(df_time, 'DimTime', 'TimeKey')

    return df_time