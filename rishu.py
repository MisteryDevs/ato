import os
import threading
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ChatJoinRequestHandler, MessageHandler, filters, ContextTypes

# Telegram Bot Configuration
TOKEN = os.getenv("TOKEN")
OWNER_ID = 6510248859

pending_requests = []
auto_approve_enabled = False
user_ids = set()
admins = set()

# Flask App Setup
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Bot is alive!"

def run_flask():
    app_flask.run(host="0.0.0.0", port=8080)

# Telegram Bot Functions
def load_admins():
    global admins
    if os.path.exists("admins.txt"):
        with open("admins.txt", "r") as f:
            admins = set(map(int, f.read().split()))
    admins.add(OWNER_ID)

def save_admins():
    with open("admins.txt", "w") as f:
        f.write(" ".join(map(str, admins)))

async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global pending_requests, auto_approve_enabled
    if auto_approve_enabled:
        try:
            await context.bot.approve_chat_join_request(update.chat_join_request.chat.id, update.chat_join_request.from_user.id)
            print(f"Auto-approved {update.chat_join_request.from_user.username or update.chat_join_request.from_user.first_name}")
        except Exception as e:
            print(e)
    else:
        pending_requests.append({
            "chat_id": update.chat_join_request.chat.id,
            "user_id": update.chat_join_request.from_user.id
        })
        print(f"Stored join request from {update.chat_join_request.from_user.username or update.chat_join_request.from_user.first_name}")

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global pending_requests
    chat_id = update.effective_chat.id
    try:
        count = int(context.args[0])
    except:
        await update.message.reply_text("❌ Please specify a valid number of users to approve.")
        return

    approved_count = 0
    new_pending = []
    for request in pending_requests:
        if approved_count < count and request["chat_id"] == chat_id:
            try:
                await context.bot.approve_chat_join_request(request["chat_id"], request["user_id"])
                approved_count += 1
            except Exception as e:
                print(e)
        else:
            new_pending.append(request)
    pending_requests = new_pending
    await update.message.reply_text(f"✅ Approved {approved_count} user(s).")

async def autoapprove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global auto_approve_enabled
    if not context.args:
        await update.message.reply_text("Usage: /autoapprove on or /autoapprove off")
        return

    mode = context.args[0].lower()
    if mode == "on":
        auto_approve_enabled = True
        await update.message.reply_text("✅ Auto-approve is now *ON*", parse_mode='Markdown')
    elif mode == "off":
        auto_approve_enabled = False
        await update.message.reply_text("⛔ Auto-approve is now *OFF*", parse_mode='Markdown')
    else:
        await update.message.reply_text("Usage: /autoapprove on or /autoapprove off")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🤖 *ApproveUsersBot Help*

/approve [number] - Approve pending join requests
/autoapprove on/off - Turn auto-approve On or Off
/help - Show help menu
/broadcast [message] - Broadcast to all users (Admin only)
/addadmin [user_id] - Add new admin
/removeadmin [user_id] - Remove an admin
/admins - Show admin list

Example: `/approve 1000`
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in admins:
        await update.message.reply_text("❌ You are not authorized to broadcast.")
        return
    if not context.args:
        await update.message.reply_text("❌ Please provide a message to broadcast.")
        return
    text = " ".join(context.args)
    success = 0
    for uid in user_ids:
        try:
            await context.bot.send_message(uid, text)
            success += 1
        except:
            pass
    await update.message.reply_text(f"✅ Broadcast sent to {success} users.")

async def addadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in admins:
        await update.message.reply_text("❌ You are not authorized.")
        return
    try:
        uid = int(context.args[0])
        admins.add(uid)
        save_admins()
        await update.message.reply_text(f"✅ Added admin {uid}.")
    except:
        await update.message.reply_text("❌ Invalid User ID.")

async def removeadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in admins:
        await update.message.reply_text("❌ You are not authorized.")
        return
    try:
        uid = int(context.args[0])
        if uid == OWNER_ID:
            await update.message.reply_text("❌ Cannot remove Owner!")
            return
        admins.discard(uid)
        save_admins()
        await update.message.reply_text(f"✅ Removed admin {uid}.")
    except:
        await update.message.reply_text("❌ Invalid User ID.")

async def show_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "**Admins List:**\n" + "\n".join(map(str, admins))
    await update.message.reply_text(msg, parse_mode="Markdown")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_ids.add(update.effective_user.id)
    await update.message.reply_text("✅ Welcome!")

def main():
    load_admins()

    # Start Flask in a separate thread
    threading.Thread(target=run_flask).start()

    # Start Telegram Bot
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(ChatJoinRequestHandler(handle_join_request))
    app.add_handler(CommandHandler("approve", approve))
    app.add_handler(CommandHandler("autoapprove", autoapprove))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("addadmin", addadmin))
    app.add_handler(CommandHandler("removeadmin", removeadmin))
    app.add_handler(CommandHandler("admins", show_admins))
    app.add_handler(CommandHandler("start", start))

    print("Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()
