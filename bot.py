import logging
from telegram import Update, ForceReply
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler
from telegram.ext import ConversationHandler

from pymongo import MongoClient
from datetime import datetime

import source.config as config
from source.bot_tools import *

MONGODB_URI = config.MONGODB_URI
BOT_TOKEN = config.BOT_TOKEN
TOKEN = BOT_TOKEN
HELIUS_KEY = config.HELIUS_KEY
HELIUS_WEBHOOK_ID = config.HELIUS_WEBHOOK_ID

ADDING_WALLET, DELETING_WALLET = range(2)
client = MongoClient(MONGODB_URI)
db = client.sol_wallets
wallets_collection = db.wallets_test

# Set up logging
logging.basicConfig(
    filename='bot.log',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
    
# Telegram Bot was created using ChatGPT, so it uses an older library (python-telegram-bot==13.7)
def welcome_message() -> str:
    message = (
        "🤖 Ahoy there, Solana Wallet Wrangler! Welcome to Solana Wallet Xray Bot! 🤖\n\n"
        "I'm your trusty sidekick, here to help you juggle those wallets and keep an eye on transactions.\n"
        "Once you've added your wallets, you can sit back and relax, as I'll swoop in with a snappy notification and a brief transaction summary every time your wallet makes a move on Solana. 🚀\n"
        "Have a blast using the bot! 😄\n\n"
        "Ready to rumble? Use the commands below and follow the prompts:"
    )

    return message

def start(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [
            InlineKeyboardButton("✨ Add", callback_data="addWallet"),
            InlineKeyboardButton("🗑️ Delete", callback_data="deleteWallet"),
            InlineKeyboardButton("👀 Show", callback_data="showWallets"),

        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        update.message.reply_text(welcome_message(), reply_markup=reply_markup)
    else:
        update.callback_query.edit_message_text("The world is your oyster! Choose an action and let's embark on this thrilling journey! 🌍", reply_markup=reply_markup)

def next(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [
            InlineKeyboardButton("✨ Add", callback_data="addWallet"),
            InlineKeyboardButton("🗑️ Delete", callback_data="deleteWallet"),
            InlineKeyboardButton("👀 Show", callback_data="showWallets"),
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="back"),
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    return reply_markup

def back_button(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [
            InlineKeyboardButton("🔙 Back", callback_data="back"),
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    return reply_markup

def button_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    if query.data == "addWallet":
        return add_wallet_start(update, context)
    elif query.data == "deleteWallet":
        return delete_wallet_start(update, context)
    elif query.data == "showWallets":
        return show_wallets(update, context)
    elif query.data == "back":
        return back(update, context)

def back(update: Update, context: CallbackContext) -> int:
    # go back to main menu from any interaction with the bot
    query = update.callback_query
    query.answer()
    query.edit_message_text("No worries! Let's head back to the main menu for more fun! 🎉")
    start(update, context)
    return ConversationHandler.END

def add_wallet_start(update: Update, context: CallbackContext) -> int:
    reply_markup = back_button(update, context)
    query = update.callback_query
    query.answer()
    query.edit_message_text("Alright, ready to expand your wallet empire? Send me the wallet address you'd like to add! 🎩", reply_markup=reply_markup)
    return ADDING_WALLET

def add_wallet_finish(update: Update, context: CallbackContext) -> int:
    reply_markup = back_button(update, context)
    wallet_address = update.message.text
    user_id = update.effective_user.id

    # check if not empty
    if not wallet_address:
        update.message.reply_text("Oops! Looks like you forgot the wallet address. Send it over so we can get things rolling! 📨", reply_markup=reply_markup)
        return

    # Validate the wallet address
    if not is_solana_wallet_address(wallet_address):
        update.message.reply_text("Uh-oh! That Solana wallet address seems a bit fishy. Double-check it and send a valid one, please! 🕵️‍♂️", reply_markup=reply_markup)
        return
    
    # Check # of transactions for the last day for this wallet
    check_res, check_num_tx = check_wallet_transactions(wallet_address)
    if not check_res:
        update.message.reply_text(f"Whoa, slow down Speedy Gonzales! 🏎️ We can only handle wallets with under 50 transactions per day. Your wallet's at {round(check_num_tx, 1)}. Let's pick another, shall we? 😉", reply_markup=reply_markup)
        return

    # Check how many wallets a user has. Limit to 5
    if wallet_count_for_user(user_id) >= 5:
        update.message.reply_text("Oops! You've reached the wallet limit! It seems you're quite the collector, but we can only handle up to 5 wallets per user. Time to make some tough choices! 😄", reply_markup=reply_markup)
        return

    # Load existing wallet data
    existing_wallet = wallets_collection.find_one(
        {
            "user_id": str(user_id),
            "address": wallet_address,
            "status": "active"
        })

    if existing_wallet:
        update.message.reply_text("Hey there, déjà vu! You've already added this wallet. Time for a different action, perhaps? 🔄", reply_markup=reply_markup)
    else:
        reply_markup = next(update, context)
        # get existing webhook from Helius
        success, webhook_id, addresses = get_webhook(HELIUS_WEBHOOK_ID)
        # update existing webhook by adding an address
        r_success = add_webhook(user_id, wallet_address, webhook_id, addresses)
        
        if (success) and (r_success):
            main = {
                "user_id": str(user_id),
                "address": wallet_address,
                "datetime": datetime.now(),
                "status": 'active',
            }
            wallets_collection.insert_one(main)
                
            update.message.reply_text("Huzzah! Your wallet has been added with a flourish! 🎉 Now you can sit back, relax, and enjoy your Solana experience as I keep an eye on your transactions. What's your next grand plan?", reply_markup=reply_markup)
        else:
            update.message.reply_text("Bummer! We hit a snag while saving your wallet. Let's give it another whirl, shall we? 🔄", reply_markup=reply_markup)

    return ConversationHandler.END


def delete_wallet_start(update: Update, context: CallbackContext) -> int:
    reply_markup = back_button(update, context)
    query = update.callback_query
    query.answer()
    query.edit_message_text("Time for some spring cleaning? Send the wallet address you'd like to sweep away! 🧹", reply_markup=reply_markup)
    return DELETING_WALLET

def delete_wallet_finish(update: Update, context: CallbackContext) -> int:
    reply_markup = next(update, context)
    wallet_address = update.message.text
    user_id = update.effective_user.id

    # check if other users have this wallet
    wallets_exist = wallets_collection.find(
        {
            "address": wallet_address,
            "status": "active"
        })
    r_success = True
    if len(list(wallets_exist)) == 1:
        logging.info('deleting unique address')
        success, webhook_id, addresses = get_webhook(HELIUS_WEBHOOK_ID)
        r_success = delete_webhook(user_id, wallet_address, webhook_id, addresses)
    else:
        logging.info('address not unique, not deleting')

    # delete from DB
    reply_markup = back_button(update, context)
    if r_success:
        result = wallets_collection.delete_one({"user_id": str(user_id), "address": wallet_address})
        if result.deleted_count == 0:
            update.message.reply_text("Hmm, that wallet's either missing or not yours. Let's try something else, okay? 🕵️‍♀️", reply_markup=reply_markup)
        else:
            update.message.reply_text("Poof! Your wallet has vanished into thin air! Now, what other adventures await? ✨", reply_markup=reply_markup)
    else:
        update.message.reply_text("Yikes, we couldn't delete the wallet. Don't worry, we'll get it next time! Try again, please. 🔄", reply_markup=reply_markup)

        return ConversationHandler.END


def show_wallets(update: Update, context: CallbackContext) -> None:
    reply_markup = next(update, context)
    user_id = update.effective_user.id

    user_wallets = list(wallets_collection.find(
        {
            "user_id": str(user_id),
            "status": "active"
        }))
    if len(user_wallets) == 0:
        update.callback_query.answer()
        update.callback_query.edit_message_text("Whoa, no wallets here! Let's add some, or pick another action to make things exciting! 🎢", reply_markup=reply_markup)
    else:
        wallet_list = "\n".join([wallet["address"] for wallet in user_wallets])
        update.callback_query.answer()
        update.callback_query.edit_message_text(f"Feast your eyes upon your wallet collection! 🎩\n\n{wallet_list}\n\nNow, what's your next move, my friend? 🤔", reply_markup=reply_markup)


def main() -> None:
    updater = Updater(TOKEN)
    dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_callback)],
        states={
            ADDING_WALLET: [MessageHandler(Filters.text & ~Filters.command, add_wallet_finish)],
            DELETING_WALLET: [MessageHandler(Filters.text & ~Filters.command, delete_wallet_finish)],
        },
        fallbacks=[CallbackQueryHandler(back, pattern='^back$')],
    )

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(conv_handler)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()