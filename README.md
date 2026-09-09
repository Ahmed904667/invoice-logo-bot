# 🧾 ASC Invoice Letterhead & Logo Adder Telegram Bot

A Python-powered Telegram Bot and offline CLI utility that automatically places the company paper design (`invoiceBg.pdf` or `invoiceBg.jpeg`) behind invoices (single or multi-page PDF documents & images) and returns the branded PDF invoice alongside an instant chat preview.

---

## 🌟 Features

- **Automatic Background Underlay**: Stamps company letterheads (PDF or Image) cleanly behind content (`overlay=False`), keeping all invoice text, tables, borders, and QR codes intact.
- **PDF & Vector Letterhead Support**: Upload high-resolution or vector PDF letterheads for crystal-clear print quality and smaller file sizes.
- **Multi-Page PDF Support**: Automatically stamps every page of multi-page invoices.
- **Instant Photo Preview**: Renders a crisp 150 DPI preview of page 1 directly in the Telegram chat.
- **Image Invoices Support**: Accepts PDF documents, JPG, PNG, and camera photos.
- **Offline CLI Utility**: Process single invoices or entire folders locally without Telegram.
- **Access Control**: Optionally restrict bot access to authorized Telegram user IDs.

---

## 🚀 Quick Start Guide

### Step 1: Create a Telegram Bot & Get Your Token

1. Open the **Telegram** app and search for `@BotFather`.
2. Start a chat and send `/newbot`.
3. Give your bot a name (e.g. `ASC Invoice Adder`).
4. Give your bot a username ending in `bot` (e.g. `asc_invoice_adder_bot`).
5. Copy the **HTTP API token** provided by BotFather (it looks like `7123456789:AAHk...`).

### Step 2: Configure `.env`

Open the `.env` file in this folder and paste your token:

```env
TELEGRAM_BOT_TOKEN=7123456789:AAHk...your_token_here...
```

### Step 3: Run the Bot

Double-click `run_bot.bat` or run in your terminal:

```bash
python bot.py
```

You should see:
```
🚀 Starting ASC Invoice Logo Adder Bot...
📁 Background template: C:\Users\pc\Desktop\logoadder\invoiceBg.jpeg
🌐 Bot access: Open to all users
✅ Bot is online and listening for invoices...
```

---

## 💬 How to Use in Telegram

1. Open your bot in Telegram and send `/start`.
2. Tap the attachment icon 📎 and send your invoice **PDF** or **Image**.
3. Within seconds, the bot replies with:
   - 📄 **`[original_name]_branded.pdf`** (Ready for print or download)
   - 👁️ **Page 1 Preview Image** (Directly visible in chat)

### Bot Commands:
- `/start` - Launch interactive bot menu & buttons
- `/help` - Usage instructions and supported file formats
- `/sample` - Test the bot with the built-in sample invoice
- `/getbg` - View and download the current background letterhead (PDF or Image)
- `/setbg` - Upload a new company letterhead (PDF or JPG/PNG image)
- `/resetbg` - Restore the previous original background if you want to undo
- `/cancel` - Cancel changing the background

---

## 💻 Offline CLI Usage (No Telegram Needed)

You can also brand invoices locally from your terminal anytime:

### Single File:
```bash
python cli.py sampleInvoice.pdf -o output_branded.pdf
```

### Batch Process an Entire Directory:
```bash
python cli.py ./my_invoices/ -o ./branded_invoices/
```

### Using a Custom Background (PDF or Image):
```bash
python cli.py sampleInvoice.pdf -b letterhead.pdf -o output.pdf
```

---

## 📦 Project Structure

```
logoadder/
├── bot.py              # Main Telegram bot application
├── processor.py        # Core PDF & image background processing engine
├── cli.py              # Command-line batch and single file processor
├── config.py           # Configuration loader (.env, paths, permissions)
├── invoiceBg.jpeg      # Company letterhead background image (ASC)
├── sampleInvoice.pdf   # Test invoice
├── requirements.txt    # Python dependencies (pymupdf, python-telegram-bot, etc.)
├── run_bot.bat         # 1-click Windows launcher
├── .env                # Your bot configuration & secret token
└── .env.example        # Configuration template
```
