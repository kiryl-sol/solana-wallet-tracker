# Try it
You can try Solana Wallet tracker here: https://t.me/solana_notify_bot

# How to run
1. Install all requirements from requirements.txt
2. Copy-paste EXAMPLE_config.py in "source", rename to "config.py" and add your Helius key, Helius webhook url (you need to create the first one manually using their dev portal), MONGODB_URI connection string to your Mongo DB, Telegram bot token (using Bot Farther bot on Telegram)

# Description of the Solana tracker

Hey everyone. Recently, I have been quite active on Solana: AMM with Tensor, weekly drops from DRiP, NFT trading, etc. 

My biggest pain for the last few weeks was the fact that Phantom notification were unreliable and not always sufficient. So I decided to build a simple Telegram bot to track any transactions happening with my wallets.

Here I want to briefly describe the process of building the bot and explain some of the architecture choices that I had to make.

First, I used Python with Flask and MongoDB. I deployed everything on a free-tier AWS EC2. The whole application has two main parts: 1) Telegram bot; 2) a server listening to Helius webhook events and sending messages to Telegram.

**Disclaimer:**

- I am not a developer. Coding is my hobby. My code can be simplistic and not well organized.
- I use ChatGPT a lot to help me with basic functionality
