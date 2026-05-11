# ⚡ FlowFetch

> A modern, clean, and lightweight desktop download manager built for fast direct-file downloads.

![FlowFetch Banner](https://github.com/EnukaSathmina/FlowFetch/blob/main/banner.png?raw=true)

---

## 🚀 Overview

**FlowFetch** is a premium-style desktop download manager built with **Python**, **PySide6**, and **SQLite**.

It is designed to make downloading direct files faster, cleaner, and more organized with a beautiful dark interface, live download tracking, queue control, history management, and local app settings.

---

## ✨ Features

- 🌐 **Direct File Downloads**  
  Download files from `http://` and `https://` direct links.

- 📊 **Live Download Tracking**  
  View real-time progress, speed, ETA, file size, and status.

- 📥 **Queue Management**  
  Manage active downloads with pause, resume, cancel, and retry controls.

- 🕘 **Download History**  
  Completed, failed, and cancelled downloads are stored locally using SQLite.

- 🧭 **Modern Dashboard**  
  See total downloads, active downloads, completed downloads, failed downloads, and current speed.

- ⚙️ **Advanced Settings Page**  
  Configure download folder, speed options, interface preferences, privacy controls, and more.

- 🎨 **Modern Dark UI**  
  Clean FlowFetch branding, smooth layout, dark theme, and beautiful icons.

- 🛡️ **Error-Safe Downloads**  
  Invalid or unreachable links show friendly errors instead of crashing the app.

---

# 🛠️ Tech Stack

FlowFetch is built with:

- Python 3.11+
- PySide6
- SQLite
- requests
- qtawesome
- PyInstaller

# 📦 Requirements

Before running FlowFetch, make sure you have:

- Python 3.11 or newer
- Windows recommended for the current desktop workflow
- Required packages from requirements.txt

# ⚙️ Installation

Clone or download this repository, then install dependencies:
```markdown
pip install -r requirements.txt
```

## ▶️ Run FlowFetch

Run the app using:
```markdown
python main.py
```
Or with the Windows Python launcher:
```markdown
py main.py
```

## 🧱 Build EXE

To package FlowFetch as a Windows desktop app:
```markdown
pyinstaller --noconfirm --onefile --windowed --icon=assets/icon.ico --name FlowFetch main.py
```
The generated executable will be available inside:
```markdown
dist/
```
The EXE will use the FlowFetch icon from:
```markdown
assets/icon.ico
```

# ⚠️ Notes
- FlowFetch is made for direct file links.
- It is not designed for full website scraping.
- Pause/resume depends on server support for: `Accept-Ranges: bytes`
- Invalid, broken, or unreachable links should show a friendly error instead of closing the app.

<div align="center">

# 👨‍💻 Developer

### Enuka Sathmina

[![GitHub](https://img.shields.io/badge/GitHub-EnukaSathmina-181717?style=for-the-badge&logo=github)](https://github.com/EnukaSathmina)

---

## ⭐ Support

If you like this project, consider giving it a star on GitHub.

⭐ **Star the repository to support the project!**

</div>

## 📜 License

All Rights Reserved.

This software and its source code are publicly visible for portfolio purposes only.  
Copying, modifying, redistributing, or commercial use is not allowed without permission.
