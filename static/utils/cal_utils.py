
def cal_percentile(df, col_name: str):
    df = df.sort_values('trade_date', ascending=False).reset_index(drop=True)
    latest_pe = df[col_name].iloc[0]
    percentile = (df[col_name] <= latest_pe).mean() * 100
    return percentile