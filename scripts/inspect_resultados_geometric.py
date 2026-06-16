import pandas as pd
p='GeoMIP/results/resultados_Geometric.xlsx'
try:
    df=pd.read_excel(p)
    cols=df.columns.tolist()
    print('COLUMNS', cols)
    if 'Alcance' in df.columns and 'Mecanismo' in df.columns:
        alc=list(df['Alcance'].dropna().unique())[:20]
        mec=list(df['Mecanismo'].dropna().unique())[:20]
        print('SAMPLE Alcance (up to 20):', alc)
        print('SAMPLE Mecanismo (up to 20):', mec)
        print('Alcance types:', list({type(x).__name__ for x in df['Alcance'].dropna().unique()}))
        print('Mecanismo types:', list({type(x).__name__ for x in df['Mecanismo'].dropna().unique()}))
    else:
        print('Alcance or Mecanismo not in columns')
except Exception as e:
    print('ERROR', repr(e))
