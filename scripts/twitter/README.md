# Twitter scraping instructions

1. Download **both** the Python script **AND** the CSV file. Place them in same folder.

2. Install `snscrape` python library by typing `pip3 install snscrape` (or similar).
    * More details on `snscrape`: https://github.com/JustAnotherArchivist/snscrape


3. Edit the `twitter_user_record_list.csv` file. 

    * Row #1 of CSV: make sure `account,last_scraped` is written
    * Rows #2 and following of CSV: Add as many twitter usernames as you want to scrape, **one username per row**. Add in this format: `<user>,`
      * Example: `standnewshk,` -  **NOTE the extra comma at the end.**
      * The extra comma is to indicate last_scraped, when the script is run, this will be updated with date/time of last scrape for this user. (i.e. it will update to `standnewshk,2021-09-25 18:34`)

    * Sample valid `twitter_user_record_list.csv` file: (**NOTE: there is nothing after the extra comma**, on standnewshk, joshuawongcf, lihkg_forum):
        ```
        account,last_scraped
        standnewshk,
        joshuawongcf,
        lihkg_forum,
        ```

4. Run script. You MUST have a `-s` argument that indicates where you want to save the Twitter backed up posts and media.

    * Example: run `python3 twitter_scraper.py -s "C:/users/hk/desktop/twitter_backup"`

5. After script is run, the following is created:

    * A: a CSV file, containing list of ALL tweets for a user
    * B: a JSON file, containing list of tweets for user **ONLY** since last scrape (if this is first time scraping user, then this JSON file will have all tweets)
    * C: a media folder, containing post image and videos 
