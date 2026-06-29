from bot.data.feed import OHLCV_COLUMNS, drop_forming_candle, ohlcv_to_df


def test_ohlcv_to_df_shapes_columns_and_time():
    rows = [
        [1700000000000, 1.0, 2.0, 0.5, 1.5, 10.0],
        [1700003600000, 1.5, 2.5, 1.0, 2.0, 12.0],
    ]
    df = ohlcv_to_df(rows)
    assert list(df.columns) == OHLCV_COLUMNS
    assert df["close"].iloc[-1] == 2.0
    assert str(df["timestamp"].dtype).startswith("datetime64")
    assert len(df) == 2


def test_drop_forming_candle_removes_last_row():
    rows = [
        [1700000000000, 1.0, 2.0, 0.5, 1.5, 10.0],
        [1700003600000, 1.5, 2.5, 1.0, 2.0, 12.0],
        [1700007200000, 2.0, 3.0, 1.5, 2.5, 14.0],
    ]
    df = ohlcv_to_df(rows)
    closed = drop_forming_candle(df)
    assert len(closed) == 2
    assert closed["close"].iloc[-1] == 2.0
