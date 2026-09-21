from datetime import datetime
import pandas as pd
def format_date(value):

    if pd.isna(value) or (type(value) == str and value.strip() == ""):
        return "--"
    if isinstance(value, (datetime, pd.Timestamp)):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return str(value)