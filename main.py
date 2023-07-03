import requests
from dotenv import load_dotenv
import os
import hmac
import time
import hashlib
from urllib.parse import urlencode


load_dotenv()

# API credentials
KEY = os.environ["BINANCE_API_KEY"]
SECRET = os.environ["BINANCE_API_SECRET"]
BASE_URL = "https://api.binance.com"

# Recipient credentials
ADDRESS = os.environ["WITHDRAWAL_ADDRESS"]
NETWORK = os.environ["WITHDRAWAL_NETWORK"]
MEMO = os.environ["WITHDRAWAL_MEMO"]
COIN = os.environ["COIN"]


""" ======  begin of functions, you don't need to touch ====== """


def hashing(query_string):
    return hmac.new(
        SECRET.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def get_timestamp():
    return int(time.time() * 1000)


def dispatch_request(http_method):
    session = requests.Session()
    session.headers.update(
        {"Content-Type": "application/json;charset=utf-8", "X-MBX-APIKEY": KEY}
    )
    return {
        "GET": session.get,
        "DELETE": session.delete,
        "PUT": session.put,
        "POST": session.post,
    }.get(http_method, "GET")


# used for sending request requires the signature
def send_signed_request(http_method, url_path, payload={}):
    query_string = urlencode(payload, True)
    if query_string:
        query_string = "{}&timestamp={}".format(query_string, get_timestamp())
    else:
        query_string = "timestamp={}".format(get_timestamp())

    url = (
        BASE_URL + url_path + "?" + query_string + "&signature=" + hashing(query_string)
    )
    print("{} {}".format(http_method, url))
    params = {"url": url, "params": {}}
    response = dispatch_request(http_method)(**params)
    return response.json()


# used for sending public data request
def send_public_request(url_path, payload={}):
    query_string = urlencode(payload, True)
    url = BASE_URL + url_path
    if query_string:
        url = url + "?" + query_string
    print("{}".format(url))
    response = dispatch_request("GET")(url=url)
    return response.json()


""" ======  end of functions ====== """


def get_coin_balance(assets, name=""):
    coin = next((coin for coin in assets if coin.get("asset") == name), None)
    if coin:
        coin_balance = float(coin["free"])
        return coin_balance
    return 0.0


def check_coin_balance_and_withdraw(coin):
    try:
        assets = send_signed_request("POST", "/sapi/v1/asset/get-funding-asset")
        amount = get_coin_balance(assets, coin)

        if amount != 0.0:
            withdrawal_params = {
                'coin': coin,
                'amount': amount,
                'network': NETWORK,
                'address': ADDRESS,
            }
            if MEMO:
                withdrawal_params["addressTag"] = MEMO

            print(send_signed_request("POST",
                                      "/sapi/v1/capital/withdraw/apply",
                                      withdrawal_params))
            return True
        else:
            print("Coin balance is zero.")
            return False
    except Exception as e:
        print(f"Error occurred: {e}")


def schedule_coin_withdraw(coin):
    interval = 7  # minutes
    check_for = 1  # minute
    while True:
        for _ in range(interval):
            if check_coin_balance_and_withdraw(coin):
                break  # Exit the loop if balance is not zero
            time.sleep(check_for * 60)
        print(f"Waiting for {interval} minutes before checking again...")
        time.sleep(interval * 60)  # Wait for 7 minutes


schedule_coin_withdraw(COIN)
