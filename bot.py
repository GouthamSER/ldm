# bot.py

import os
import time
import asyncio
import threading
import shutil
import subprocess
from datetime import timedelta

from pyrogram import Client, filters, enums
from pyrogram.types import Message
from pyrogram.errors import FloodWait

import aria2p
from aiohttp import web

# ================= HEALTH CHECK IMPORTS (MODULARIZED) =================
# We try to import the web server logic from the new module
try:
    from plugins.weblive import start_web_server_thread
    UVICORN_AVAILABLE = True
except ImportError as e:
    # This will catch if the module or its dependencies (uvicorn/starlette) are missing
    print("WARNING: Could not import web server module 'plugins.weblive'. Health check will not run.")
    print(f"Import error details: {e}")
    UVICORN_AVAILABLE = False
# ======================================================================

# ================= CONFIG =================
API_ID = int(os.getenv("API_ID", "18979569"))
API_HASH = os.getenv("API_HASH", "45db354387b8122bdf6c1b0beef93743")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8559651884:AAEUeSpqxunq9BE6I7cvw8ced7J0Oh3jk34")

DOWNLOAD_DIR = os.path.abspath("downloads")
ARIA2_PORT = 6801
HEALTH_PORT = int(os.getenv("PORT", 8000))
ARIA2_SECRET = "gjxdml"

# ================= CLEANUP =================
def cleanup():
    if os.path.exists(DOWNLOAD_DIR):
        shutil.rmtree(DOWNLOAD_DIR)
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

cleanup()

# ================= ARIA2 =================
aria2 = aria2p.API(
    aria2p.Client(
        host="http://localhost",
        port=ARIA2_PORT,
        secret=ARIA2_SECRET
    )
)

# ================= GLOBAL STATE =================
ACTIVE = {}  # Tracks GID for both download and upload
DOWNLOAD_COUNT = 0
UPLOAD_COUNT = 0
TOTAL_DOWNLOAD_TIME = 0
TOTAL_UPLOAD_TIME = 0
DOWNLOAD_COUNTER = 1  # Global counter for numbering downloads (1, 2, 3, ...)

def time_tracker():
    """Increments total time spent downloading or uploading."""
    global TOTAL_DOWNLOAD_TIME, TOTAL_UPLOAD_TIME
    while True:
        if DOWNLOAD_COUNT > 0:
            TOTAL_DOWNLOAD_TIME += 1
        if UPLOAD_COUNT > 0:
            TOTAL_UPLOAD_TIME += 1
        time.sleep(1)

# Start the time tracking thread
threading.Thread(target=time_tracker, daemon=True).start()

# ================= HELPERS =================
def progress_bar(done, total, size=12):
    """Generates a 12-segment progress bar string using ■ and □."""
    FILLED = "■"  # Filled square
    EMPTY = "□"   # Empty square
    
    if total == 0:
        return f"[{EMPTY * size}] 0.00%"
        
    percent = min(100.0, (done / total) * 100)
    filled_count = int(percent / 100 * size)
    
    if percent > 0 and filled_count == 0 and size > 0:
        filled_count = 1
        
    if filled_count > size:
        filled_count = size
        
    empty_count = size - filled_count
    bar = FILLED * filled_count + EMPTY * empty_count
    
    return f"[{bar}] {percent:.2f}%"

def time_fmt(sec):
    # This helper is used for ETA and total time display
    if not isinstance(sec, (int, float)):
        sec = 0
    m, s = divmod(int(sec), 60)
    h, m = divmod(m, 60)
    
    # Format h/m/s for total time: Hh Mm Ss
    if h > 0:
        return f"{h}h{m}m{s}s"
    elif m > 0:
        return f"{m}m{s}s"
    else:
        return f"{s}s"

def format_speed(bps):
    if bps == 0:
        return "0B/s"
    units = ['B/s', 'KB/s', 'MB/s', 'GB/s', 'TB/s', 'PB/s']
    unit = 0
    while bps >= 1024 and unit < len(units) - 1:
        bps /= 1024
        unit += 1
    return f"{bps:.1f}{units[unit]}"

def format_size(b): 
    if b == 0:
        return "0B"
    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    unit = 0
    while b >= 1024 and unit < len(units) - 1:
        b /= 1024
        unit += 1
    return f"{b:.2f}{units[unit]}"

# ================= BOT =================
app = Client(
    "aria2-leech-bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=16
)

@app.on_message(filters.command("start"))
async def start(_, m):
    PARSE_MODE = enums.ParseMode.MARKDOWN
    user_name = m.from_user.first_name

    start_message = (
        f"👋 Hello, **{user_name}**!\n"
        "I am a fast Aria2 Leech Bot designed to download files directly from URLs and upload them to Telegram.\n\n"
        "**📚 How to Use Me:**\n"
        "┠ To start a download: `/l <Direct_URL>`\n"
        "┠ To check my status: `/stats`\n"
        "┠ To cancel an active task (DL or UL): `/cancel<index>_<gid>`\n\n"
        "**ℹ️ Supported URLs:**\n"
        "┖ Direct file links (HTTP/HTTPS) and Torrent files.\n\n"
        "🚀 Happy Leeching!"
    )
    await reply_message_async(m, start_message, parse_mode=PARSE_MODE)

async def edit_message_async(msg, content, parse_mode, max_retries=3):
    """Edit message with robust FloodWait handling."""
    if msg.text == content:
        return None  # Skip editing if content hasn't changed
    
    retries = 0
    while retries < max_retries:
        try:
            return await msg.edit(content, parse_mode=parse_mode)
        except FloodWait as e:
            print(f"Hit FloodWait in edit_message_async: Waiting for {e.value} seconds... (Retry {retries+1}/{max_retries})")
            await asyncio.sleep(e.value)
            retries += 1
        except Exception as edit_error:
            print(f"Error editing message: {edit_error}")
            return None
    print("Max retries exceeded for editing message.")
    return None

async def reply_message_async(m, text, parse_mode=None, max_retries=3):
    """Reply to message with robust FloodWait handling."""
    retries = 0
    while retries < max_retries:
        try:
            return await m.reply(text, parse_mode=parse_mode)
        except FloodWait as e:
            print(f"Hit FloodWait in reply_message_async: Waiting for {e.value} seconds... (Retry {retries+1}/{max_retries})")
            await asyncio.sleep(e.value)
            retries += 1
        except Exception as reply_error:
            print(f"Error replying message: {reply_error}")
            return None
    print("Max retries exceeded for replying message.")
    return None

async def upload_file(msg, file_path, name, file_size, loop, gid, download_index, user_first, user_id):
    global UPLOAD_COUNT
    UPLOAD_COUNT += 1
    try:
        await app.send_document(
            msg.chat.id, 
            file_path,
            caption=f"✅ **{name}**\nSize: {format_size(file_size)}",
            progress=upload_progress, 
            progress_args=(gid, time.time(), name, enums.ParseMode.MARKDOWN, loop, download_index, user_first, user_id)
        )
        
        # If upload completes successfully
        await edit_message_async(msg, f"✅ Upload complete for **{name}**!", parse_mode=enums.ParseMode.MARKDOWN)
    
    except Exception as e:
        print(f"Upload failed: {e}")
        
        # Skip final error message if manual cancel occurred
        if not ACTIVE.get(gid, {}).get("cancel", False):
            await edit_message_async(msg, f"❌ Upload failed: {str(e)}", parse_mode=None)
    
    finally:
        UPLOAD_COUNT -= 1
        # Clean up the entry from ACTIVE
        ACTIVE.pop(gid, None) 
        
        if os.path.exists(file_path):
            await asyncio.to_thread(os.remove, file_path)

@app.on_message(filters.command(["l", "leech"]))
async def leech(_, m: Message):
    global DOWNLOAD_COUNT, DOWNLOAD_COUNTER
    PARSE_MODE = enums.ParseMode.MARKDOWN

    if len(m.command) < 2:
        return await reply_message_async(m, "Usage:\n/l <direct_url>", parse_mode=None)

    url = m.command[1]
    
    try:
        options = {
            "dir": DOWNLOAD_DIR,
            "max-connection-per-server": "4",
            "min-split-size": "1M",
            "split": "4",
            "max-concurrent-downloads": "10"
        }
        dl = await asyncio.to_thread(aria2.add_uris, [url], options)
        gid = dl.gid
    except Exception as e:
        print(f"Aria2 Add URI Failed: {e}")
        return await reply_message_async(m, f"Failed to start download: {e}", parse_mode=None)

    # Assign a download index
    download_index = DOWNLOAD_COUNTER
    DOWNLOAD_COUNTER += 1

    start_time = time.time()
    msg = await reply_message_async(m, f"🚀 Starting download {download_index}\nGID: `{gid}`", parse_mode=PARSE_MODE)
    # Store GID and cancel flag for download phase
    ACTIVE[gid] = {"cancel": False, "start_time": start_time}
    DOWNLOAD_COUNT += 1
    
    while not dl.is_complete:
        if ACTIVE[gid]["cancel"] or dl.is_removed or dl.has_failed:
            await edit_message_async(msg, f"Download {gid} finished, removed, or failed.", parse_mode=None)
            break
            
        await asyncio.to_thread(dl.update) 
        
        done = dl.completed_length
        total = dl.total_length
        speed = dl.download_speed
        eta = dl.eta

        if isinstance(eta, timedelta):
            eta_seconds = eta.total_seconds()
        else:
            eta_seconds = eta
        
        eta_str = time_fmt(eta_seconds)
        elapsed = int(time.time() - start_time)
        elapsed_str = time_fmt(elapsed)

        if not (dl.is_removed or dl.has_failed):
            try:
                # DOWNLOAD MESSAGE TEMPLATE (MATCHING EXAMPLE FORMAT)
                await edit_message_async(
                    msg,
                    f"{download_index}. {dl.name}\n"
                    f"┃ {progress_bar(done, total)}\n" 
                    f"┠ Processed: {format_size(done)} of {format_size(total)}\n"
                    f"┠ Status: Download | ETA: {eta_str}\n"
                    f"┠ Speed: {format_speed(speed)} | Elapsed: {elapsed_str}\n"
                    f"┠ Engine: Aria2 v1.36.0\n"
                    f"┠ Mode: #Leech | #Aria2\n"
                    f"┠ Seeders: N/A | Leechers: N/A\n"
                    f"┠ User: {m.from_user.first_name} | ID: {m.from_user.id}\n"
                    f"┖ /cancel{download_index}_{gid}", 
                    parse_mode=None  # No markdown needed for this format
                )
            except Exception as edit_error:
                print(f"Error editing message: {edit_error}")

        await asyncio.sleep(3)  # Throttle edits to avoid FloodWait

    # Download finished, reset flag
    DOWNLOAD_COUNT -= 1
    
    # Remove GID from active tasks after download is done/failed
    ACTIVE.pop(gid, None) 

    if dl.is_complete and dl.files and dl.files[0]:
        file_path = dl.files[0].path
        
        if not file_path or not os.path.exists(file_path):
            await edit_message_async(msg, "❌ Download complete but file missing.", parse_mode=None)
        else:
            try:
                file_size = os.path.getsize(file_path)
                if file_size == 0:
                    raise ValueError("File empty")
            except:
                await edit_message_async(msg, "❌ File corrupted or empty.", parse_mode=None)
            else:
                # TRANSITION MESSAGE
                await edit_message_async(msg, 
                                            f"✅ Download complete! Starting upload of **{dl.name}**\n"
                                            f"To cancel upload, use `/cancel{download_index}_{gid}`", 
                                            parse_mode=PARSE_MODE)
                
                # Store GID, file path, and cancel flag for upload phase tracking
                ACTIVE[gid] = {"cancel": False, "file_path": file_path, "name": dl.name, "last_edit": 0, "msg": msg}
                
                # Start upload in background (concurrent with other tasks)
                loop = asyncio.get_running_loop()
                user_first = m.from_user.first_name
                user_id = m.from_user.id
                asyncio.create_task(upload_file(msg, file_path, dl.name, file_size, loop, gid, download_index, user_first, user_id))
    
    elif dl.has_failed:
        await edit_message_async(msg, f"❌ Download **{dl.name}** failed.\nReason: {dl.error_message}", parse_mode=PARSE_MODE)

@app.on_message(filters.regex(r"^/cancel"))
async def cancel(_, m: Message):
    # Parse the task_id: /cancel or /cancel2_gid -> extract gid after first _
    text = m.text
    if "_" in text:
        task_id = text.split("_", 1)[1]
    else:
        task_id = text.replace("/cancel", "")

    if not task_id:
        return await reply_message_async(m, "Invalid cancel command.", parse_mode=None)

    if task_id in ACTIVE:
        task_info = ACTIVE[task_id]
        if "file_path" in task_info:  # Upload cancellation
            task_info["cancel"] = True
            file_path = task_info.get("file_path")
            if file_path and os.path.exists(file_path):
                await asyncio.to_thread(os.remove, file_path)
            await reply_message_async(m, f"🛑 Cancelled Upload **{task_info['name']}**.\nFile deleted.", parse_mode=enums.ParseMode.MARKDOWN)
        else:  # Download cancellation
            ACTIVE[task_id]["cancel"] = True
            try:
                dl = await asyncio.to_thread(aria2.get_download, task_id)
                await asyncio.to_thread(aria2.remove, [dl], force=True)
            except Exception as e:
                # Ignore exception if download wasn't in aria2's list anymore
                print(f"Error removing Aria2 download: {e}")
            await reply_message_async(m, f"🛑 Cancelled Download GID: **{task_id}**", parse_mode=enums.ParseMode.MARKDOWN)
    else:
        await reply_message_async(m, f"Task ID **{task_id}** not found or already complete.", parse_mode=enums.ParseMode.MARKDOWN)

def upload_progress(current, total, gid, start_time, name, parse_mode, loop, download_index, user_first, user_id):
    if total == 0:
        return
    
    # CANCELLATION CHECK (must raise an exception to stop pyrogram's upload)
    if ACTIVE.get(gid, {}).get("cancel", False):
        # This exception stops the Pyrogram thread immediately.
        raise Exception("Upload manually cancelled by user.")
    
    # Throttle edits to every 3 seconds to avoid FloodWait and prevent blocking
    current_time = time.time()
    if current_time - ACTIVE.get(gid, {}).get("last_edit", 0) < 3:
        return  # Skip editing if less than 3 seconds have passed
    
    elapsed = time.time() - start_time
    speed = current / elapsed if elapsed > 0 else 0
    eta = (total - current) / speed if speed > 0 else 0
    eta_str = time_fmt(eta)
    elapsed_str = time_fmt(elapsed)
    progress_bar_output = progress_bar(current, total)
    
    # UPLOAD MESSAGE TEMPLATE (MATCHING EXAMPLE FORMAT)
    new_content = (
        f"{download_index}. {name}\n"
        f"┃ {progress_bar_output}\n"
        f"┠ Processed: {format_size(current)} of {format_size(total)}\n"
        f"┠ Status: Upload | ETA: {eta_str}\n"
        f"┠ Speed: {format_speed(speed)} | Elapsed: {elapsed_str}\n"
        f"┠ Engine: Pyrogram v2\n"
        f"┠ Mode: #Leech | #qBit\n"
        f"┠ User: {user_first} | ID: {user_id}\n"
        f"┖ /cancel{download_index}_{gid}"
    )
    
    msg = ACTIVE[gid]["msg"]
    try:
        coro = edit_message_async(msg, new_content, parse_mode)
        asyncio.run_coroutine_threadsafe(coro, loop)
        # Update last edit time
        ACTIVE[gid]["last_edit"] = current_time
    except:
        pass

@app.on_message(filters.command("stats"))
async def bot_stats(_, m: Message):
    # ================= 1. System Stats (Subprocess) =================
    
    cpu_percent = "N/A"
    ram_usage = "N/A"
    disk_info = "Disk info unavailable"
    
    # Get CPU Load
    try:
        # Get total CPU percentage (user + system)
        cpu_result = subprocess.run(
            ["sh", "-c", "top -bn1 | grep 'Cpu(s)' | awk '{print $2 + $4}'"], 
            capture_output=True, text=True, timeout=5, check=True
        )
        if cpu_result.returncode == 0:
            cpu_percent = f"{float(cpu_result.stdout.strip()):.1f}%"
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, ValueError, Exception):
        pass

    # Get RAM Usage
    try:
        # Get percentage of used RAM
        ram_result = subprocess.run(
            ["sh", "-c", "free -m | awk 'NR==2{printf \"%.1f%%\", $3*100/$2 }'"], 
            capture_output=True, text=True, timeout=5, check=True
        )
        if ram_result.returncode == 0:
            ram_usage = ram_result.stdout.strip()
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, ValueError, Exception):
        pass

    # Get Disk Usage
    try:
        # df -h output: Filesystem | Size | Used | Avail | Use% | Mounted on
        df_result = subprocess.run(
            ["df", "-h", "--output=size,avail,pcent", DOWNLOAD_DIR], 
            capture_output=True, text=True, timeout=5, check=True
        )
        if df_result.returncode == 0:
            # Skip header, get the line with the stats
            df_output_lines = df_result.stdout.strip().split('\n')
            if len(df_output_lines) > 1:
                df_data = df_output_lines[1].split() 
                if len(df_data) >= 3:
                    total_disk = df_data[0]
                    free_disk = df_data[1]
                    disk_percent = df_data[2]
                    # Example: F: 10G [12%] (F=Free, T=Total)
                    disk_info = f"F: {free_disk} | T: {total_disk} [{disk_percent}]"
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, Exception):
        pass

    # ================= 2. Bot State and Time =================

    # Get uptime
    uptime_sec = time.time() - app.start_time
    uptime_str = time_fmt(uptime_sec)
    
    # Format total cumulative times
    total_dl_str = time_fmt(TOTAL_DOWNLOAD_TIME)
    total_ul_str = time_fmt(TOTAL_UPLOAD_TIME)

    # Count active tasks
    active_download = DOWNLOAD_COUNT
    active_upload = UPLOAD_COUNT
    
    # ================= 3. Build Message =================

    stats_text = (
        "🤖 **Bot Status Report**\n"
        "--- System Metrics ---\n"
        f"┠ CPU Load: **{cpu_percent}**\n"
        f"┠ RAM Usage: **{ram_usage}**\n"
        f"┖ Disk: **{disk_info}**\n"
        "\n"
        "--- Transfer Activity ---\n"
        f"┠ Active DLs: **{active_download}**\n"
        f"┖ Active ULs: **{active_upload}**\n"
        "\n"
        "--- Cumulative Stats ---\n"
        f"┠ Total DL Time: **{total_dl_str}**\n"
        f"┠ Total UL Time: **{total_ul_str}**\n"
        f"┖ Bot Uptime: **{uptime_str}**"
    )
    
    await reply_message_async(m, stats_text, parse_mode=enums.ParseMode.MARKDOWN)
    
if __name__ == "__main__":
    try:
        aria2.get_stats()
        print("✅ Aria2 connected on port 6801!\n")
    except:
        print("❌ Aria2 not running!\n")
        exit(1)
    
    print("🤖 Bot is starting...\n")

    # Store bot start time for uptime calculation
    app.start_time = time.time()
    
    # Start the Uvicorn/Starlette health check in a separate thread
    if UVICORN_AVAILABLE:
        # Call the function imported from plugins.weblive
        start_web_server_thread(HEALTH_PORT)
    
    app.run()
