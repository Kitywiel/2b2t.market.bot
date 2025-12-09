# 2b2t Market Discord Bot

A Discord bot for the 2b2t marketplace.

## Setup Instructions

### Prerequisites
- Python 3.8 or higher installed on your Windows laptop
- A Discord account
- Administrator access to a Discord server (to add the bot)

### Step 1: Create a Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to the "Bot" section in the left sidebar
4. Click "Add Bot"
5. Under the bot's username, click "Reset Token" and copy the token (keep this secret!)
6. Enable these Privileged Gateway Intents:
   - Presence Intent
   - Server Members Intent
   - Message Content Intent
7. Go to the "OAuth2" > "URL Generator" section
8. Select scopes: `bot`
9. Select bot permissions: `Administrator` (or customize as needed)
10. Copy the generated URL and open it in your browser to invite the bot to your server

### Step 2: Configure the Bot

1. Create a file named `.env` in this directory (copy from `.env.example`)
2. Add your bot token to the `.env` file:
   ```
   DISCORD_BOT_TOKEN=your_actual_bot_token_here
   ```

### Step 3: Install Dependencies

Open Command Prompt or PowerShell in this directory and run:
```bash
pip install -r requirements.txt
```

### Step 4: Run the Bot

```bash
python bot.py
```

## Available Commands

- `!hello` - Bot responds with a greeting
- `!ping` - Shows the bot's latency
- `!info` - Displays bot information
- `!help` - Shows all available commands

## Customization

You can add more commands by adding functions decorated with `@bot.command()` in `bot.py`.

## Troubleshooting

- **Bot not responding**: Make sure Message Content Intent is enabled in the Discord Developer Portal
- **Import errors**: Ensure you've installed the requirements with `pip install -r requirements.txt`
- **Token errors**: Double-check that your token is correctly copied into the `.env` file

## Running on Windows Startup (Optional)

To run the bot automatically when Windows starts:

1. Press `Win + R`, type `shell:startup`, and press Enter
2. Create a shortcut to a batch file that runs the bot
3. Create `start_bot.bat` with:
   ```batch
   @echo off
   cd /d "C:\path\to\2b2t.market.bot"
   python bot.py
   pause
   ```
4. Place the shortcut in the Startup folder
