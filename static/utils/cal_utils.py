def cal_percentile(df, col_name: str):
    # 检查数据框是否为空
    if len(df) == 0 or df['trade_date'].isnull().all():
        return -1

    # 按日期排序并过滤掉col_name中的空值
    df_sorted = df.sort_values('trade_date', ascending=False)
    df_filtered = df_sorted[df_sorted[col_name].notna()]

    # 检查过滤后是否有数据
    if len(df_filtered) == 0:
        return -1

    # 获取最新的非空值并计算分位数
    latest_number = df_filtered[col_name].iloc[0]
    percentile = (df_filtered[col_name] <= latest_number).mean() * 100

    return percentile