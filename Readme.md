## 🚀 Aria2 Leech Telegram Bot

A high-performance Telegram bot built with **Pyrogram** and integrated with **Aria2** for fast, direct-link downloading (leeching) and seamless uploading to Telegram chats.

### ✨ Features

* **Fast Downloading:** Utilizes Aria2, a powerful command-line download utility, for high-speed downloads (supporting multi-connection).
* **Real-time Progress:** Provides live progress updates for both download and Telegram upload phases, including speed, ETA, and progress bar.
* **Concurrent Tasks:** Supports multiple simultaneous downloads and uploads.
* **Stats Command:** Displays essential system metrics (CPU, RAM, Disk usage) and bot activity statistics.
* **Cancellation:** Allows users to cancel active download or upload tasks.
* **Health Check:** Includes a web health check endpoint for deployment on platforms like Heroku/Render.

### ⚙️ Prerequisites

* A Telegram API Key (`API_ID` and `API_HASH`).
* A Telegram Bot Token (`BOT_TOKEN`).
* A running **Aria2** daemon accessible on `http://localhost:6801` with RPC enabled. (For cloud deployment, ensure Aria2 is running in the same container/environment).
* Python 3.10+

### 🛠️ Setup and Installation

#### 1. Clone the repository

```bash
git clone https://github.com/GouthamJosh/tg-leech
cd 1dm
bash start.sh
```
Give Credits To [Goutham Josh](https://t.me/im_goutham_josh) ✔❤<br>
Fork it Light Weight Repo !!!
