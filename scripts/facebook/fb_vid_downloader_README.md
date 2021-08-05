# FB Vid Downloader

This script downloads FB videos in their highest quality for backup purpose. You must provide it a `.txt` file with a list of Facebook Video URLs to download (ex: `https://www.facebook.com/watch/?v=319284099859384`).

## FEATURES
1. Downloads the highest quality version of the video automatically
2. Skip video if downloaded already, produces list of downloaded videos
3. Detect temporary blocks from FB, and try again when temporary block is cancelled



## REQUIREMENTS: 
You MUST install:
1. Selenium AND Chrome Webdriver. See Step 1 to 3 here: https://medium.com/@patrick.yoho11/installing-selenium-and-chromedriver-on-windows-e02202ac2b08
2. Progressist, for download progress bar: https://pypi.org/project/progressist/
3. Pandas, for CSV file handling.
4. You must also have Chrome.



## INSTRUCTIONS:
1. Log in to Facebook with Chrome.
2. Switch to English version of FB. See [here](https://www.facebook.com/help/327850733950290/)
3. Quit Chrome, once logged in to FB.
4. Run script. You can run either with arguments (see below), or without any arguments (the script will then ask you questions about video you want to download).
5. The first time you run script, Chrome will not be logged in to Facebook. Log in to Facebook.
6. Videos are downloaded. The progress bar shows progress of downloading one particular video. It shows time since download start, and time left to download finish.
7. When script is finished, check "archive" .txt file for any videos that had error when downloading. Then redownload them.

**NOTE**: For some videos, this script will download the video and audio files **SEPARATELY** (due to the way Facebook build their videos). **If there is both a `<fb_video_id>_video.mp4` and `<fb_video_id>_audio.mp4` file (same ID), after downloading the video and audio file, you must combine them together using a tool, like FFMpeg.**
Here is one possible way to do it with FFMpeg: https://superuser.com/questions/277642/how-to-merge-audio-and-video-file-in-ffmpeg

Search on Google for other ways. This will be fixed in future version.




## REQUIRED ARGUMENTS:
1. `-u` or `--url_txt`: Path to .txt file containing list of FB Video URLs, like https://www.facebook.com/watch?v=856580768116475.
(ex: 'C:/users/<yourusername>/standnews_fb_vids.txt')

2. `-fo` or `--folder`: Path to folder to save videos in
(ex: C:/users/<yourusername>/Desktop/standnews_fb_vids)

3. `-o` or `--org_name`: Name of organization, used for file naming
(ex: standnews)

4. `-fb` or `--fb_user`: Username of FB profile you are downloading 
(ex: for https://www.facebook.com/standnewshk/, it is "standnewshk")

Example: `python3 fb_vid_downloader.py -u 'C:/users/myusername/Desktop/list_of_fb_vid_urls.txt' -fo 'C:/users/myusername/backupfolder' -o standnews -fb standnewshk`



## OPTIONAL ARGUMENTS:
1. `--start`: start downloading FB vids, from a particular line in the --url_txt file (i.e. skip the first X lines). ex: `--start 1000`.
2. `--end`: end downloading FB videos at a particular line in url_txt file. ex: `--end 2000`.
3. `-cp` or `--chrome_path`: Path to Chrome profile folder. Use only if your Chrome profile folder is not in the default folder (most people don't need this). See here: https://www.howtogeek.com/255653/how-to-find-your-chrome-profile-folder-on-windows-mac-and-linux/
4. `-cn` or `--chrome_name`: Chrome profile name. Use if you have multiple profiles. only if your Chrome profile folder is not in the default folder (most people don't need this). See https://www.guidingtech.com/things-about-google-chrome-profiles/
5. `-d` or `--debug`: Print debug messages.



## TROUBLESHOOTING:
If script has error:
1. Try restarting computer, then run this script (without opening Chrome first).
2. Make sure your path to Chrome user profile folder is correct: https://www.howtogeek.com/255653/how-to-find-your-chrome-profile-folder-on-windows-mac-and-linux/
3. Make sure your Chrome user profile name is correct (it is usually `Default`).
  
## QUESTIONS?
Open an [issue](https://github.com/backup4hk/backup4hk/issues).
