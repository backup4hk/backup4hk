# 下載 Instagram Post Script

本 script 能夠下載備份任何公開 instagram account 的 post，包括 post 的照片、影片與 post metadata.

## Features 功能
1. 自動下載照片與影片最高 resolution 版本. 照片下載出來格式 是 .png, 而影片便是 .mp4.
2. 能下載 post 的 caption, like 數目、comment 數目 、post 日期、和 post 所有相關 metadata (comment內容不支持), 而 metadata output 格式 是 .csv 與 .json
4. 自動 rate limit 你下載速度而便避免被 instagram temporary blocked

## Quick Start Guide 說明
**STEP 1. 先下載整個 folder 共 3 個 python file**

**STEP 2. extract 你 instagram account 個 cookie file**

  由於 instagram API 需要 authentication (登入) 才能使用, 所以 script 需要你 IG account cookie file 便使用登入 API。如果對 account 私隱有顧慮，建議註冊新太空 IG account 來用。

1. 先要安裝一個 firefox 或 chrome extension 來 extract IG cookie file。  
    * Firefox 可以安裝 [Cookie Quick Manager](https://addons.mozilla.org/en-US/firefox/addon/cookie-quick-manager/)
    * Chrome 可以安裝 [Edit This Cookie](https://chrome.google.com/webstore/detail/editthiscookie/fngmhnnpilhplaeedifhccceomclgfbg?hl=en)
2. 安裝後，使用 firefox 或 chrome 去 instagram.com 登入。
3. 登入 Instagram 後，打開 cookie extension （cookie extension 應該位於你 browser 右上邊), 然後尋找 instagram.com cookies.
4. 你會見到有至少 9 個 instagram cookie, 分別為:

    * mid
    * ig_did
    * ig_nrcb
    * csrftoken
    * ds_user_id
    * sessionid
    * shbid
    * shbts
    * rur
    * (如果有其他 cookie, 可以忽略)

    而每個 cookie 會有一個 value, 例如 mid cookie 個 value 可能是 abcdefghi123.

5. 把以上 9 個 cookie 個 value copy and paste 入 `ig_download_posts.py` script 裡面的 COOKIES variable. COOKIES variable 格式為:

    `mid=<insert mid>; ig_did=<insert ig_did>; ig_nrcb=<insert ig_nrcb>; csrftoken=<insert csrf token>; ds_user_id=<insert ds_user_id>; sessionid=<insert sessionid>; shbid="<insert shbid>"; shbts="<insert shbts>"; rur="<insert rur>"`

    注意: `shbid`, `shbts`, `rur` 個 value 左右兩邊要加個 double quotation marks: `“ "` 

**STEP 3. 運行 python script**

* 去 command prompt 或 terminal run 以下 command： `python3 ig_download_posts.py`

**STEP 4. 如何答 script 問題**

* 下載某個賬戶所有 post 按 1
* （2 和 3 是 debugging features, 暫時不會提供説明）
* 下載多 post 的賬戶 (例如立場新聞、蘋果日報) 可能需要 2+ 小時，請耐心等候。
