from pymongo import MongoClient
import requests
from datetime import datetime
import source.config as config
import logging

from datetime import datetime

# Set up logging
logging.basicConfig(
    filename='bot.log',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

MONGODB_URI = config.MONGODB_URI
BOT_TOKEN = config.BOT_TOKEN
TOKEN = BOT_TOKEN
HELIUS_KEY = config.HELIUS_KEY
HELIUS_WEBHOOK_URL = config.HELIUS_WEBHOOK_URL

client = MongoClient(MONGODB_URI)
db = client.sol_wallets
wallets_collection = db.wallets_test

def get_webhook():
    # Get current webhook from Helius. We can use one webhook to track all addresse
    url = f'https://api.helius.xyz/v0/webhooks?api-key={HELIUS_KEY}'
    r = requests.get(url)
    if r.status_code == 200:
        return True, r.json()[0]['webhookID'], r.json()[0]['accountAddresses']
    else:
        logging.info('error get webhook')
        return False

def add_webhook(user_id, user_wallet, webhook_id, addresses):
    # Update current webhook from Helius by adding the new address
    url = f"https://api.helius.xyz/v0/webhooks/{webhook_id}?api-key={HELIUS_KEY}"
    if user_wallet in addresses:
        logging.info('existing wallet, returning true')
        return True
    addresses.append(user_wallet)
    data = {
        "webhookURL": "https://y12sbdpq09.execute-api.us-east-1.amazonaws.com/wallet",
        "accountAddresses": addresses,
        "transactionTypes":["Any"],
        "webhookType": "enhanced",
    }
    r = requests.put(url, json=data)
    if r.status_code == 200:
        return True
    else:
        return False

def delete_webhook(user_id, user_wallet, webhook_id, addresses):
    # Delete this address from the current webhook from Helius
    url = f"https://api.helius.xyz/v0/webhooks/{webhook_id}?api-key={HELIUS_KEY}"
    if user_wallet not in addresses:
        return True
    addresses.remove(user_wallet)
    data = {
        "webhookURL": HELIUS_WEBHOOK_URL,
        "accountAddresses": addresses,
        "transactionTypes":["Any"],
        "webhookType": "enhanced",
    }
    r = requests.put(url, json=data)
    if r.status_code == 200:
        return True
    else:
        return False
    
def is_solana_wallet_address(address):
    # Check if this address looks like a solana wallet
    base58_chars = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
    address_length = [32, 44]
    if len(address) < address_length[0]:
        return False

    if len(address) > address_length[1]:
        return False

    for char in address:
        if char not in base58_chars:
            return False

    return True

def wallet_count_for_user(user_id: int) -> int:
    # Check how many addresses this user has
    wallet_count = wallets_collection.count_documents({"user_id": str(user_id), "status": "active"})
    return wallet_count

def check_wallet_transactions(wallet):
    # Check # transaction per day for this wallet
    # If fails - return True
    try:
        url = f'https://api.helius.xyz/v0/addresses/{wallet}/raw-transactions?api-key={HELIUS_KEY}'
        r = requests.get(url)
        j = r.json()
        if len(j) < 10:
            return True, 0
        first_date = datetime.utcfromtimestamp(j[-1]['blockTime'])
        current_date = datetime.now()
        num_txs = len(j)
        delta = (current_date - first_date).total_seconds()
        av_per_day = num_txs / delta * 86400
        if av_per_day > 50:
            return False, av_per_day
        else:
            return True, av_per_day
    except:
        logging.info('ERROR checking wallet txs')
        return True, 0