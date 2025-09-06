import json
from datetime import datetime, timedelta, timezone

from flask import Flask, request

from static.service.daily_report_service import get_trade_day_info

app = Flask(__name__)


@app.route('/')
def hello_world():  # put application's code here
    return 'Hello World!'


@app.route('/beforeOpenDailyInfo')
def before_open_daily_info():  # put application's code here
    date = request.args.get('date')
    date_str = ''
    if date is None or date == 'null' or date == 'None':
        date_str = (datetime.now(timezone.utc) + timedelta(hours=8)).strftime("%Y-%m-%d")
    else:
        date_str = date
    return json.dumps(get_trade_day_info(date_str).__dict__, indent=2, ensure_ascii=False)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9090)
