import json
from datetime import datetime

from flask import Flask

from static.service.daily_report_service import get_trade_day_info

app = Flask(__name__)


@app.route('/')
def hello_world():  # put application's code here
    return 'Hello World!'

@app.route('/beforeOpenDailyInfo')
def before_open_daily_info(date_str: str = datetime.now().strftime("%Y-%m-%d")):  # put application's code here
    return json.dumps(get_trade_day_info(date_str).__dict__, indent=2, ensure_ascii=False)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9090)
