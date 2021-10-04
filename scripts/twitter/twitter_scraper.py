'''
Scrape Twitter post text, post metadata, image and video 
Last updated: 2021-10-03
See README before running script 
'''

# Imports
import os, subprocess, pandas as pd, re, sys, logging, json, argparse
from urllib.parse import urlparse
import urllib.request
from datetime import datetime
from urllib.error import HTTPError

logger = logging.getLogger(__name__)
now_datetime = datetime.now().astimezone()
now_as_string = now_datetime.strftime('%Y-%m-%d_%H%M')
now_as_string_for_record_csv = now_datetime.strftime('%Y-%m-%d %H:%M:%S %z')

# Helper functions
# =============================================

# Get user input 
def get_input_variables():
	while True:
		try:
			pull_all_usernames = input("Enter 1 to pull a single user's tweets. Enter 2 to pull tweets of all users listed in record_csv.\n")
			if pull_all_usernames != '1' and pull_all_usernames != '2':
				print("Invalid input! Only 1 or 2 is accepted! Try again!")
				continue

			if pull_all_usernames == '1':
				SINGLE_USERNAME = input("Enter Twitter username to download:\n")
				if SINGLE_USERNAME == '':
					print("Username cannot be empty! Try again!")
					continue
			elif pull_all_usernames == '2':
				SINGLE_USERNAME = None
			
			DOWNLOAD_ALL_POSTS = input("Download all posts? Y for Yes, N for No: (No means: script will only download new posts that have not been archived previously. This will save time.)\n")
			if DOWNLOAD_ALL_POSTS.lower() != 'y' and DOWNLOAD_ALL_POSTS.lower() != 'n':
				print("Invalid input! Only Y or N is accepted. Try again!")
				continue
			if DOWNLOAD_ALL_POSTS.lower() == 'y':
				DOWNLOAD_ALL_POSTS = True
			elif DOWNLOAD_ALL_POSTS.lower() == 'n':
				DOWNLOAD_ALL_POSTS = False

			SAVE_FOLDER = input("\nEnter path to save Twitter posts in (leave blank for this folder):\n")

			RECORD_CSV_FILE_PATH = input("\nEnter path to Twiiter lastpull record CSV file (leave blank for default of 'twitter_user_record_list.csv'). See README.\n")

			# debug mode
			DEBUG_MODE = input("\nPrint debugging statements on screen? Y for yes, or N for no: \n")
			if DEBUG_MODE.lower() != 'y' and DEBUG_MODE.lower() != 'n':
				logger.info("Invalid input! Only Y or N is accepted. Try again!")
				continue
			if DEBUG_MODE.lower() == 'y':
				DEBUG_MODE = True
			elif DEBUG_MODE.lower() == 'n':
				DEBUG_MODE = False

		except ValueError as e:
			logger.info("Invalid input! Try again!")
			continue

		return_dict = {
			'SINGLE_USERNAME': SINGLE_USERNAME,
			'DOWNLOAD_ALL_POSTS': DOWNLOAD_ALL_POSTS,
			'SAVE_FOLDER': SAVE_FOLDER,
			'RECORD_CSV_FILE_PATH': RECORD_CSV_FILE_PATH,
			'DEBUG_MODE': DEBUG_MODE,
		}
		return return_dict 

# Create a record CSV file
def create_record_csv(RECORD_CSV_FILE_PATH, SINGLE_USERNAME):
	try:
		data = [[SINGLE_USERNAME, '']]
		record_csv_df = pd.DataFrame(data, columns=['account','last_scraped'])
		record_csv_df.to_csv(RECORD_CSV_FILE_PATH, sep=',', index=False)
		return record_csv_df
	except Exception as e:
		logger.critical(f'Error creating CSV record file! Exiting!\nError: {str(e)}')
		sys.exit()

# Pull list of users to scrape.
def open_record_csv(RECORD_CSV_FILE_PATH, SINGLE_USERNAME=None):
	# The CSV at RECORD_CSV_FILE_PATH lists [1] the users we want to scrape, and [2] when this user was last scraped.
	# [2] makes the script faster, as the script will NOT pull any posts before <date/time when we did last scrape for this user>.
	# Ex: if we last scraped standnewshk on 2021-09-01 18:30, next time we scrape it, we will not pull tweets before 2021-09-01 18:30.
	try:
		record_csv_df = pd.read_csv(RECORD_CSV_FILE_PATH)

		# if you are pulling tweets for one single user, and he doesn't exist in record_csv_df, add him
		if SINGLE_USERNAME is not None and SINGLE_USERNAME not in record_csv_df['account'].values:
			record_csv_df = record_csv_df.append({'account': SINGLE_USERNAME, 'last_scraped': ''}, ignore_index=True)

		return record_csv_df
	except FileNotFoundError as e:

		# If we are pulling a single user:
		if SINGLE_USERNAME is not None:
			create_csv = input(f'No Twitter user record CSV found at {RECORD_CSV_FILE_PATH}! Do you want to create one to pull {SINGLE_USERNAME}? Y for Yes, N for No. If you indicated a Twitter user record CSV in a previous question, you probably entered an incorrect path; press N and try again. N will exit the script. Otherwise, enter Y to continue.\n').lower()

			if create_csv != 'y' and create_csv != 'n':
				logger.critical('Invalid input entered! You must enter Y or N! Exiting!')
				sys.exit()
			elif create_csv == 'y':
				record_csv_df = create_record_csv(RECORD_CSV_FILE_PATH, SINGLE_USERNAME)
				return record_csv_df
			else:
				logger.critical('N entered. Not creating a record CSV file. You must create your own record CSV file to run script (see README). Exiting script!')
				sys.exit()
		else:
			logger.critical(f'No Twitter user record CSV found at {RECORD_CSV_FILE_PATH}! You must create a Twitter user record CSV file, and in the CSV, list the users you want to pull Twitter posts for. See README. Exiting script!')
			sys.exit()

	except Exception as e:
		logger.critical(f'Could not read Twitter user record CSV at {RECORD_CSV_FILE_PATH}! Try running script again! Exiting!')
		sys.exit()

# Scrape twitter posts (post text and metadata, ex: # of retweets, date/time, etc).
# if SINGLE_USERNAME is specified, then scrape posts for only 1 twitter account.  
# Otherwise, scrape for all accounts listed in record_csv.
def scrape_posts(record_csv_df, DOWNLOAD_ALL_POSTS=False, SINGLE_USERNAME=None):

	logger.info('Start Twitter scraping')

	# Define variables to track progress
	# =======================================
	scraping_counter = 0 # Keep track of progress of number of users we have scraped
	
	if SINGLE_USERNAME is not None:
		number_of_users = 1
	else:
		number_of_users = len(record_csv_df)
	number_of_new_tweets_scraped = 0
	list_of_users_scraped = []
	list_of_users_scraped_with_new_tweets = []

	# For every row (twitter account) listed in record_csv, run twitter scraper.
	for index, row in record_csv_df.iterrows():

		# If we only want to scrape for one single user, then skip all rows that are not that user
		if SINGLE_USERNAME is not None and row['account'] != SINGLE_USERNAME:
			continue

		scraping_counter += 1

		username = row['account']
		last_scraped = row['last_scraped']
		# print('last scraped:')
		# print(last_scraped)

		logger.info(f'Scraping: Start #{scraping_counter}/{number_of_users}: {username}. Last scraped: {last_scraped}')

		# Run twitter scrapper
		# =====================================
		# If no last_scraped, then it's the first time pulling tweets for this acct, so pull everything.
		# Useful arguments for snscrape:
		# a. --since DATETIME
		# b. --progress (printed to stderr)
		if last_scraped == None or pd.isnull(row['last_scraped']) or last_scraped == '' or DOWNLOAD_ALL_POSTS == True:
			if DOWNLOAD_ALL_POSTS == True:
				logger.debug("Downloading all posts for this account...")
			else:
				logger.debug("First time scraping this account. Downloading all posts...")
			cmd = subprocess.run(["snscrape", "--jsonl", "twitter-user", username], capture_output=True,text=True)
		# Otherwise, pull only since last pull
		else:
			cmd = subprocess.run(["snscrape", "--jsonl", "--since", last_scraped, "twitter-user",  username],capture_output=True,text=True)

		# if command returned an error, log error, continue to next user
		if cmd.returncode != 0:
			logger.error(f'Scraping: Error scraping: #{scraping_counter}/{number_of_users}: {username}, {cmd.stderr}')
			continue

		list_of_users_scraped.append(username)


		# Write json file of tweets
		# ================================================
		# Write json file only if there are new tweets since last scrape
		if cmd.stdout != '' and cmd.stdout != None: # Check if there are tweets since last scrape
			list_of_users_scraped_with_new_tweets.append(username)

			if not os.path.exists(f'{SAVE_FOLDER}/{username}/chunks/'):
				os.makedirs(f'{SAVE_FOLDER}/{username}/chunks/')

			# Write json file. This JSON file will ONLY contain tweets since last scrape.
			with open(f'{SAVE_FOLDER}/{username}/chunks/twitter_{username}_{now_as_string}.json','w') as json_f:
				json_f.write(cmd.stdout)

			# Create a CSV file, from the json we generated just above
			tweets_df = pd.read_json(f'{SAVE_FOLDER}/{username}/chunks/twitter_{username}_{now_as_string}.json', lines=True)

			# CSV export 
			# ================================================
			# Export dataframe into a CSV
			# Append existing CSV file, if any
			csv_file_path = SAVE_FOLDER + '/' + username + '/twitter_' + username + '.csv'
			logger.debug(f'CSV file path: {csv_file_path}')

			tweets_df = tweets_df.replace(r'\n',' ', regex=True) 
			number_of_new_tweets_scraped += tweets_df.shape[0]
			
			logger.info(f'Writing new tweets for {username}...')
			if os.path.exists(csv_file_path):
				csv_df = pd.read_csv(csv_file_path, parse_dates=['date'])
				if DOWNLOAD_ALL_POSTS == False:
					csv_df = csv_df.append(tweets_df, ignore_index = True) # append all pulled tweets to csv ONLY if download_all_posts is false
				else:
					# Go through every new tweet that was pulled. If this tweet exists in csv_df already, drop this tweet's row in csv_df, then reappend latest version from tweets_df.
					for tweets_df_index, tweets_df_row in tweets_df.iterrows():
						tweet_id = tweets_df_row['id']
						if tweet_id in csv_df['id'].values:
							# Drop this tweet in csv_df, then reappend with latest version of the tweet
							csv_df.drop(csv_df[csv_df.id == tweet_id].index, inplace=True)
							csv_df = csv_df.append(tweets_df_row, ignore_index=True)

				csv_df = csv_df.sort_values('date', ascending=False) # Sort csv by date
				csv_df.to_csv(csv_file_path, sep=',', index=False)
			else:
				tweets_df.to_csv(csv_file_path, sep=',', index=False)

		# Else: there were no new tweets pulled.
		else:
			logger.info(f"Scraping #{scraping_counter}/{number_of_users}, {username}: No new tweets. CSV was not updated, and no JSON file created.")

		# Update this user's record in record_csv to show we just scraped.
		record_csv_df.loc[record_csv_df['account'] == username, 'last_scraped'] = now_as_string_for_record_csv
		record_csv_df.to_csv(RECORD_CSV_FILE_PATH, sep=',', index=False)

		logger.info(f'Done scraping #{scraping_counter}/{number_of_users}: {username}')

	logger.info(f'Done Twitter scraping for all users')
	return {
		'number_of_users_scraped': scraping_counter,
		# New is defined as: tweets never seen before, OR all tweets if download_all is True
		'number_of_new_tweets_scraped': number_of_new_tweets_scraped,
		'list_of_users_scraped': list_of_users_scraped,
		'list_of_users_scraped_with_new_tweets': list_of_users_scraped_with_new_tweets,
	}

# Download images and videos on posts
# if SINGLE_USERNAME is specified, then download imgs/vids for only 1 twitter account.  
# Otherwise, download imgs/vids for all accounts listed in record_csv.
def download_media(record_csv_df, SINGLE_USERNAME=None):
	logger.info('Start Twitter media download')

	# Define variables to track progress
	# =======================================
	if SINGLE_USERNAME is not None:
		number_of_users = 1
	else:
		number_of_users = len(record_csv_df)
	media_user_counter = 0
	number_of_media_total = 0
	number_of_new_media = 0
	list_of_users_scraped = []
	list_of_users_scraped_with_new_media = []

	# if you are pulling tweets for one single user, and he doesn't exist in record_csv_df, add him
	if SINGLE_USERNAME is not None and SINGLE_USERNAME not in record_csv_df['account'].values:
		record_csv_df = record_csv_df.append({'account': SINGLE_USERNAME}, ignore_index=True)

	# For every account in record_csv, download its Twitter media (images and csv).
	for index, row in record_csv_df.iterrows():
		
		# If we only want to scrape for one single user, then skip all rows that are not that user
		if SINGLE_USERNAME is not None and row['account'] != SINGLE_USERNAME:
			continue

		username = row['account']

		media_user_counter += 1
		list_of_users_scraped.append(username)
		
		logger.info(f'Start media download, user #{media_user_counter}/{number_of_users}: {username}.')

		# Define paths to files
		CSV_FILE_PATH = SAVE_FOLDER + '/' + username + '/twitter_' + username + '.csv'
		MEDIA_ALREADY_DOWNLOADED_LIST_FILE_PATH = SAVE_FOLDER + '/' + username + '/media/' + username + '_media_already_downloaded.txt'
		ERROR_URL_LIST_FILE_PATH = SAVE_FOLDER + '/' + username + '/media/' + username + '_error_urls_' + now_as_string + '.txt'

		# Read CSV file, media column
		try:
			csv_media_df = pd.read_csv(CSV_FILE_PATH, usecols=['media'], dtype={"media": "string"})
			csv_media_df = csv_media_df['media'].dropna()
			csv_media_df = csv_media_df[csv_media_df != 'media'] # drop all rows that say "media"
		except FileNotFoundError as e:
			logger.warning(f'No CSV found for user #{media_user_counter}/{number_of_users}, {username}, skipping media download for {username}!')
			continue

		# the Media column contains a number of JSONs, interpret these JSONs, and add them to json_obj
		json_of_all_media_urls = []
		for entry in csv_media_df:
			entry = entry.replace('\'','"')
			entry = entry.replace('None','"None"')

			json_of_all_media_urls.append(json.loads(entry))

		urls_to_download = []
		video_counter = 0
		photo_counter = 0



		#print(json_obj)

		# Extract video and photo URLs from JSON file.
		for entry in json_of_all_media_urls:

			# Extract video and image URLs from JSON file.
			for item in entry:
				number_of_media_total += 1

				if item['_type'] == 'snscrape.modules.twitter.Video':
					video_counter += 1

					highest_bitrate = 0
					highest_bitrate_url = ''

					for video in item['variants']:
						try:
							if int(video['bitrate']) > highest_bitrate:
								highest_bitrate = video['bitrate']
								highest_bitrate_url = video['url']
						except ValueError:
							continue

					urls_to_download.append([highest_bitrate_url,'video'])
					logger.debug(f'Found video: {highest_bitrate_url}, bitrate: {highest_bitrate}')

				# Extract photo
				elif item['_type'] == 'snscrape.modules.twitter.Photo':
					photo_counter += 1
					urls_to_download.append([item['fullUrl'],'photo'])
					logger.debug(f'Found photo #{photo_counter} URL in json file: ' + item['fullUrl'])

		# Create media folder to store media
		if not os.path.exists(SAVE_FOLDER + '/' + username + '/media'):
			os.makedirs(SAVE_FOLDER + '/' + username + '/media')

		# Open and read list of already downloaded media files/URLs
		if os.path.isfile(MEDIA_ALREADY_DOWNLOADED_LIST_FILE_PATH):
			with open(MEDIA_ALREADY_DOWNLOADED_LIST_FILE_PATH,'r') as f:
				downloaded_files = f.readlines()
				f.close()
		else:
			downloaded_files = []

		# Download media
		# ====================================================
		download_counter = 0
		total_video_and_photo = video_counter + photo_counter

		for url_obj in urls_to_download:

			download_counter += 1
			url = url_obj[0]
			media_type = url_obj[1] # Photo or video

			# If pic/video already downloaded, continue
			if (url + '\n') in downloaded_files:
				logger.info(f'Already downloaded! Media download, user #{media_user_counter}/{number_of_users}, {username}: {download_counter}/{total_video_and_photo} ({url})')
				continue

			# Pic/video has not been downloaded
			path = urlparse(url).path
			number_of_new_media += 1

			if username not in list_of_users_scraped_with_new_media:
				list_of_users_scraped_with_new_media.append(username)

			# Download photo
			if media_type == 'photo':
				ext = re.search('format=(.*?)&',url).group(1)

				logger.info(f'Media download, user #{media_user_counter}/{number_of_users}, {username}: Downloading #{download_counter}/{total_video_and_photo}... {url}')
				
				try:
					urllib.request.urlretrieve(url, SAVE_FOLDER + '/' + username + '/media/ ' + path.rsplit("/",1)[-1] + '.' + ext)

					# Log that this URL is now downloaded
					with open(MEDIA_ALREADY_DOWNLOADED_LIST_FILE_PATH,'a') as f:
						f.write(url + '\n')
						f.close()

				except Exception as e:
					logger.warning(f'Media download, user #{media_user_counter}/{number_of_users}, {username}: Error #{download_counter}/{total_video_and_photo}: {str(e)}. {url}')

					# Log that this URL had error when downloading
					with open(ERROR_URL_LIST_FILE_PATH,'a') as f:
						f.write(url + '\n')
						f.close()

			# Download video
			elif media_type == 'video':
				logger.info(f'Media download, user #{media_user_counter}/{number_of_users}, {username}: Downloading #{download_counter}/{total_video_and_photo}... {url}')
				try:
					urllib.request.urlretrieve(url, SAVE_FOLDER + '/' + username + '/media/ ' + path.rsplit("/",1)[-1])

					# Log that this URL is now downloaded
					with open(MEDIA_ALREADY_DOWNLOADED_LIST_FILE_PATH,'a') as f:
						f.write(url + '\n')
						f.close()

				except Exception as e:
					logger.warning(f'Media download, user #{media_user_counter}/{number_of_users}, {username}: Error #{download_counter}/{total_video_and_photo}: {str(e)}. {url}')

					# Log that this URL had error when downloading
					with open(ERROR_URL_LIST_FILE_PATH,'a') as f:
						f.write(url + '\n')
						f.close()
		

	logger.info('Done Twitter media download')

	return {
		"number_of_users_scraped": media_user_counter,
		"number_of_media_total": number_of_media_total,
		"number_of_new_media": number_of_new_media,
		"list_of_users_scraped": list_of_users_scraped,
		"list_of_users_scraped_with_new_media": list_of_users_scraped_with_new_media,
	}

# Run script 
# ================================================
if __name__ == '__main__':
	# Initialize argument parser
	parser = argparse.ArgumentParser()
	# Required argument
	parser.add_argument("-s", "--save_location", dest="SAVE_FOLDER", help="Save location for Twitter backup")
	# Optional argument
	parser.add_argument("-u", "--username", dest="SINGLE_USERNAME", help="Username of single Twitter profile to scrape. Leave blank to scrape ALL twitter users listed in Record CSV file (see README) path to CSV containing list of Twitter users to scrape (see README)")
	# Optional argument
	parser.add_argument("-r", "--record_csv_file_path", dest="RECORD_CSV_FILE_PATH", help="File path to CSV containing list of Twitter users to scrape (see README)", default="twitter_user_record_list.csv")
	# Optional argument
	parser.add_argument("-a", "--download_all_posts", dest="DOWNLOAD_ALL_POSTS",
						action="store_true", default=False, help="Download all posts, including posts that have been archived before")
	# Optional argument
	parser.add_argument("-d", "--debug", dest="DEBUG_MODE",
						action="store_true", default=False, help="Print debug messages")


	args = parser.parse_args()

	if len(sys.argv) > 1:
		SAVE_FOLDER = args.SAVE_FOLDER
		SINGLE_USERNAME = args.SINGLE_USERNAME
		DOWNLOAD_ALL_POSTS = args.DOWNLOAD_ALL_POSTS
		RECORD_CSV_FILE_PATH = args.RECORD_CSV_FILE_PATH
		DEBUG_MODE = args.DEBUG_MODE

		if SAVE_FOLDER == '':
			SAVE_FOLDER = os.getcwd()

	elif len(sys.argv) == 1:
		input_variables = get_input_variables()
		SINGLE_USERNAME = input_variables['SINGLE_USERNAME']
		DOWNLOAD_ALL_POSTS = input_variables['DOWNLOAD_ALL_POSTS']
		SAVE_FOLDER = input_variables['SAVE_FOLDER']
		RECORD_CSV_FILE_PATH = input_variables['RECORD_CSV_FILE_PATH']
		DEBUG_MODE = input_variables['DEBUG_MODE']

	# Logging
	# =================================================
	if DEBUG_MODE is True:
		logger.setLevel(logging.DEBUG)
	else:
		logger.setLevel(logging.INFO)
	formatter = logging.Formatter('%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s')

	# Logging to stdout
	stream_handler = logging.StreamHandler()
	stream_handler.setLevel(logging.DEBUG)
	logger.addHandler(stream_handler)
	stream_handler.setFormatter(formatter)


	# Main script
	# ==================================================

	if SINGLE_USERNAME != None:
		record_csv_df = open_record_csv(RECORD_CSV_FILE_PATH, SINGLE_USERNAME)
		# Scrape posts
		scraping_results = scrape_posts(record_csv_df, DOWNLOAD_ALL_POSTS, SINGLE_USERNAME)
		# Download media
		download_results = download_media(record_csv_df, SINGLE_USERNAME)
	else:
		record_csv_df = open_record_csv(RECORD_CSV_FILE_PATH)
		# Scrape posts
		scraping_results = scrape_posts(record_csv_df, DOWNLOAD_ALL_POSTS)
		# Download media
		download_results = download_media(record_csv_df)
