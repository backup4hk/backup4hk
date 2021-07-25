# To get list of all videos on youtube:

### Instructions

1. Install [youtube-dl](https://github.com/ytdl-org/youtube-dl)
2. Run the following in Command Prompt or Terminal: `youtube-dl --get-filename -o "%(upload_date)s;;;;;%(view_count)s;;;;;%(id)s;;;;;%(title)s" "[YT channel URL]" > playlist.csv`

**Example:** `youtube-dl --get-filename -o "%(upload_date)s;;;;;%(view_count)s;;;;;%(id)s;;;;;%(title)s" "https://www.youtube.com/user/icablehk/videos" > playlist.csv`

**Notes:**
* **With an ID: To view the Youtube video, do: `https://www.youtube.com/watch?v=[id]`. Example: `https://www.youtube.com/watch?v=vVOk7oIKOts`**
* You can also get other metadatas too (url, timestamp, like_count, etc), see: https://github.com/ytdl-org/youtube-dl#output-template
* Recommend to use 5 semicolons `;;;;;` instead of 1 comma ` , ` to separate/delimit the csv file, as many youtube videos have comma ` , ` or 1 semicolon ` ; `. This means if you use 1 comma or semicolon to delimit, the delimiting will be wrong.
