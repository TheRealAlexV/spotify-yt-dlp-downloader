# TODO


### **Core Functionality**

* ☐ Smart search: search YT by keywords
* ☐ Auto-match best YT result for a Spotify track
* ☐ Multi-threaded downloads (with safe throttling)
* ☐ Pre-download audio preview (5–10 seconds)
* ☐ Auto-redownload corrupted files
* ☐ Download album art from somewhere
* ☐ Generate M3U playlists automatically
* ☐ Detect & skip unavailable tracks
* ☐ Auto-convert any format → desired format

---

### **Library Management**

* ☐ Folder organization by Artist/Album/Year
* ☐ Auto-rename files based on metadata patterns
* ☐ Detect mismatched metadata
* ☐ Duplicate finder across entire library
* ☐ “Missing album art” scanner
* ☐ Music library size statistics
* ☐ Sort library by bitrate/format/duration

---

### **Config & Automation**

* ☑ Auto-update settings with validation
* ☑ Profile-based config (light, advanced, minimal)
* ☑ Auto-run scheduled syncs with Spotify export folder
* ☑ Auto cleanup after each run
* ☑ Configurable retry rules
* ☑ Auto-create backups of JSON files

---

### **Data & Analytics**

* ☐ Progress reports (daily/weekly download stats)
* ☐ Time estimation for batch downloads
* ☐ Average bitrate and file size stats
* ☐ "Most failed artists" report
* ☐ Export structured logs (JSON/CSV)

---

### **User Experience**

* ☐ Download queue visualization
* ☐ Skippable animated progress bar
* ☐ Minimal/verbose mode
* ☐ Light/dark terminal color theme
* ☐ Error explanations & fixes
* ☐ Interactive “wizard mode” for new users
* ☐ Auto-open folder when finished (optional)

---

### **Safety & Reliability**

* ☐ Download rate limiting
* ☐ Temporary file cleanup
* ☐ Ensure atomic writes to JSON
* ☐ Safe lock system for preventing double-run
* ☐ Crash recovery states

---

### **Integrations**

* ☐ Discord/Telegram notifications after batch jobs
* ☐ Local Web UI dashboard (Flask/FastAPI)
* ☐ Import Spotify playlists via public links
* ☐ Sync with Last.fm (scrobble metadata)
* ☐ MusicBrainz lookup for metadata corrections

---

### **Developer & Maintenance Tools**

* ☐ Unit tests for main modules
* ☐ CI/CD linting and formatting
* ☐ Command to reset app state
* ☐ Fast debug mode bypassing menus
* ☐ Plugin system for community extensions
