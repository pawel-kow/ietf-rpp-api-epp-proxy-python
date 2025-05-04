import datetime

def check_datetime_format_utc_and_delta(ref_datetime, date_string, delta_seconds_min, delta_seconds_max):
    delta_sec = (datetime.datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=datetime.UTC) - ref_datetime).total_seconds()
    ret = delta_sec >= delta_seconds_min and delta_sec <= delta_seconds_max
    if ret is False:
        print(f'check_datetime_format_utc_and_delta failed: {ref_datetime} {date_string} {delta_sec} not in [{delta_seconds_min}, {delta_seconds_max}]')
    return ret