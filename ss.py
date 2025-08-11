import os, asyncio, json, random, re, sys
from datetime import datetime, timedelta
from telethon import TelegramClient, events, functions

# ------------------- تنظیمات -------------------
API_ID = 2040
API_HASH = "b18441a1ff607e10a989891a5462e627"
SESSION_DIR = "sessions"
os.makedirs(SESSION_DIR, exist_ok=True)

ENEMIES_FILE = "enemies.json"
enemies = set(json.load(open(ENEMIES_FILE))) if os.path.exists(ENEMIES_FILE) else set()

enemy_responses = [
    "کیر تو کس ننت",
    "خاله خارکصه",
    "خاله کص خار",
    "ننت از افق کوروش بیشتر مشتری داره",
    "ننه زیبا",
    "ننه صورتی",
    "انقد ننت سکسیه شورتش رو انداختم رو آنتن سوپر پخش کرد",
    "کیر تو خاندانت"
]

bad_words = ["مادر", "کصننت", "کص ننت", "مادر جنده", "بی ناموص", "کص ننه", "سیک"]

silent_mode = False
time_mode = False
clients = []

# ------------------- محدودیت زمانی -------------------
START_DATE = datetime.now()
EXPIRY_DATE = START_DATE + timedelta(days=30)

def check_access():
    if datetime.now() > EXPIRY_DATE:
        print("⛔ اعتبار این اسکریپت تمام شده.")
        sys.exit()

# ------------------- ذخیره دشمن -------------------
def save_enemies():
    with open(ENEMIES_FILE, "w") as f:
        json.dump(list(enemies), f)

# ------------------- ساخت فونت ساعت -------------------
def stylize_time():
    now = datetime.now().strftime("%H:%M")
    digits = {"0":"𝟎","1":"𝟏","2":"𝟐","3":"𝟑","4":"𝟒","5":"𝟓","6":"𝟔","7":"𝟕","8":"𝟖","9":"𝟗",":":" : "}
    return "".join(digits.get(ch, ch) for ch in now) + " ❆"

# ------------------- تغییر اسم با ساعت -------------------
async def update_name(client):
    global time_mode
    while time_mode:
        me = await client.get_me()
        base_name = me.first_name.split(" | ")[0]
        await client(functions.account.UpdateProfileRequest(first_name=f"{base_name} | {stylize_time()}"))
        await asyncio.sleep(180)

# ------------------- اضافه و حذف دشمن -------------------
async def register_handlers(client):
    global silent_mode, time_mode

    @client.on(events.NewMessage(pattern="(?i)^this is$", outgoing=True))
    async def add_enemy(event):
        if event.is_reply:
            uid = (await event.get_reply_message()).sender_id
            enemies.add(uid)
            save_enemies()
            await event.respond("✅ به لیست دشمنان اضافه شد")

    @client.on(events.NewMessage(pattern="(?i)^this is not$", outgoing=True))
    async def remove_enemy(event):
        if event.is_reply:
            uid = (await event.get_reply_message()).sender_id
            enemies.discard(uid)
            save_enemies()
            await event.respond("❌ از لیست دشمنان حذف شد")

    @client.on(events.NewMessage(incoming=True))
    async def reply_enemy(event):
        if event.sender_id in enemies:
            await event.reply(random.choice(enemy_responses))

    @client.on(events.NewMessage(incoming=True))
    async def reply_to_badwords(event):
        if "وینستون" in event.raw_text.lower():
            if any(bad in event.raw_text for bad in bad_words):
                await event.reply(random.choice(enemy_responses))

    # ذخیره مدیا
    @client.on(events.NewMessage(pattern="(?i)^up$", outgoing=True))
    async def download_media(event):
        if event.is_reply:
            msg = await event.get_reply_message()
            if msg.media:
                gallery_path = "/storage/emulated/0/DCIM/Camera"
                os.makedirs(gallery_path, exist_ok=True)
                path = await msg.download_media(file=gallery_path)
                os.system(f'am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d "file://{path}"')
                await event.respond(f"📥 ذخیره شد: {os.path.basename(path)}")

    # pvspam
    @client.on(events.NewMessage(outgoing=True))
    async def spam_message(event):
        m = re.match(r"(.+)-(\d+)-$", event.raw_text)
        if m:
            for _ in range(int(m.group(2))):
                await event.respond(m.group(1))
            await event.delete()

    # سایلنت
    @client.on(events.NewMessage(pattern="(?i)^undn$", outgoing=True))
    async def disable_silent(event):
        silent_mode = False
        await event.respond("🔊 سایلنت غیرفعال شد")

    @client.on(events.NewMessage(pattern="(?i)^dn$", outgoing=True))
    async def enable_silent(event):
        silent_mode = True
        await event.respond("🔇 سایلنت فعال شد")

    @client.on(events.NewMessage(incoming=True))
    async def silent_handler(event):
        if silent_mode:
            await event.delete()
            await event.client.delete_messages(event.chat_id, [event.id], revoke=True)

    # ساعت
    @client.on(events.NewMessage(pattern="(?i)^on time$", outgoing=True))
    async def enable_time(event):
        global time_mode
        time_mode = True
        asyncio.create_task(update_name(client))
        await event.respond("⏳ نمایش ساعت فعال شد")

    @client.on(events.NewMessage(pattern="(?i)^of time$", outgoing=True))
    async def disable_time(event):
        global time_mode
        time_mode = False
        await event.respond("❌ نمایش ساعت غیرفعال شد")

# ------------------- مانیتورینگ سشن‌ها -------------------
async def watch_sessions():
    known_sessions = set(os.listdir(SESSION_DIR))
    while True:
        current_sessions = set(os.listdir(SESSION_DIR))

        # اضافه شدن سشن جدید
        new_files = [f for f in current_sessions - known_sessions if f.endswith(".session")]
        for file in new_files:
            session_path = os.path.join(SESSION_DIR, file)
            client = TelegramClient(session_path, API_ID, API_HASH)
            await client.start()
            await register_handlers(client)
            clients.append(client)
            print(f"✅ اکانت جدید اضافه شد: {file}")
            asyncio.create_task(client.run_until_disconnected())

        # حذف سشن قدیمی
        removed_files = [f for f in known_sessions - current_sessions if f.endswith(".session")]
        for file in removed_files:
            for c in clients:
                if os.path.basename(c.session.filename) == file:
                    await c.disconnect()
                    clients.remove(c)
                    print(f"❌ اکانت حذف شد: {file}")

        known_sessions = current_sessions
        await asyncio.sleep(10)

# ------------------- اجرای اصلی -------------------
async def main():
    # فعال‌کردن اکانت‌های موجود
    for file in os.listdir(SESSION_DIR):
        if file.endswith(".session"):
            session_path = os.path.join(SESSION_DIR, file)
            client = TelegramClient(session_path, API_ID, API_HASH)
            await client.start()
            await register_handlers(client)
            clients.append(client)
            asyncio.create_task(client.run_until_disconnected())

    # شروع مانیتورینگ پوشه سشن‌ها
    asyncio.create_task(watch_sessions())

    print("✅ همه اکانت‌ها فعال شدند.")
    while True:
        await asyncio.sleep(60)

if __name__ == "__main__":
    check_access()
    asyncio.run(main())
