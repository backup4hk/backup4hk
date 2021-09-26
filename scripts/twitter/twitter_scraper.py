'''
Scrape Twitter post text, post metadata, image and video 
Last updated: 2021-09-24
See README before running script 
'''

# Imports
import os, subprocess, pandas as pd, re, sys, logging, json, argparse
from urllib.parse import urlparse
import urllib.request
from datetime import datetime
from urllib.error import HTTPError

# Helper functions
# =============================================

# Pull list of users to scrape.
def open_record_csv(RECORD_CSV_FILE_PATH):
	# The CSV at RECORD_CSV_FILE_PATH lists [1] the users we want to scrape, and [2] when this user was last scraped.
	# [2] makes the script faster, as the script will NOT pull any posts before <date/time when we did last scrape for this user>.
	# Ex: if we last scraped standnewshk on 2021-09-01 18:30, next time we scrape it, we will not pull tweets before 2021-09-01 18:30.
	try:
		record_csv = pd.read_csv(RECORD_CSV_FILE_PATH)
		return record_csv
	except FileNotFoundError as e:
		logger.critical(f'No Twitter user record CSV found at {RECORD_CSV_FILE_PATH}! You must create a Twitter user record CSV file, and in the CSV, list the users you want to pull Twitter posts for. See README. Exiting script!')
		sys.exit()
	except Exception as e:
		logger.critical(f'Could not read Twitter user record CSV at {RECORD_CSV_FILE_PATH}! Try running script again! Exiting!')
		sys.exit()


# Scrape twitter posts (post text and metadata, ex: # of retweets, date/time, etc), for all accounts listed in record_csv.
def scrape_posts(record_csv):
	scraping_counter = 0 # Keep track of progress of number of users we have scraped
	logger.info('Start Twitter scraping')
	number_of_users = len(record_csv)

	# For every row (twitter account) listed in record_csv, run twitter scraper.
	for index, row in record_csv.iterrows():
		scraping_counter += 1

		username = row['account']
		last_scraped = row['last_scraped']

		logger.info(f'Scraping: Start #{scraping_counter}/{number_of_users}: {username}. Last scraped: {last_scraped}')

		# Run twitter scrapper
		# =====================================
		# If no last_scraped, then it's the first time pulling tweets for this acct, so pull everything.
		# Useful arguments for snscrape:
		# a. --since DATETIME
		# b. --progress (printed to stderr)
		if last_scraped == None or pd.isnull(row['last_scraped']):
			logger.debug("First time scraping this account.")
			cmd = subprocess.run(["snscrape", "--jsonl", "twitter-user", username], capture_output=True,text=True)
		# Otherwise, pull only since last pull
		else:
			cmd = subprocess.run(["snscrape", "--jsonl", "--since", last_scraped, "twitter-user",  username],capture_output=True,text=True)

		# if command returned an error, log error, continue to next user
		if cmd.returncode != 0:
			logger.error(f'Scraping: Error scraping: #{scraping_counter}/{number_of_users}: {username}, {cmd.stderr}')
			continue

		# Write json file of tweets
		# ================================================
		# Write json file only if there are new tweets since last scrape
		if cmd.stdout != '' and cmd.stdout != None: # Check if there are tweets since last scrape
			if not os.path.exists(f'{SAVE_FOLDER}/{username}/'):
				os.makedirs(f'{SAVE_FOLDER}/{username}/')

			# Write json file. This JSON file will ONLY contain tweets since last scrape.
			with open(f'{SAVE_FOLDER}/{username}/twitter_{username}_{now_as_string}.json','w') as json_f:
				json_f.write(cmd.stdout)

			# Create a CSV file, from the json we generated just above
			tweets_df = pd.read_json(SAVE_FOLDER + '/' + username + '/twitter_' + username + '_' + now_as_string + '.json', lines=True)

			# CSV export 
			# ================================================
			# Export dataframe into a CSV
			# Append existing CSV file, if any
			csv_file_path = SAVE_FOLDER + '/' + username + '/twitter_' + username + '.csv'
			logger.debug(f'CSV file path: {csv_file_path}')

			if os.path.exists(csv_file_path):
				logger.info(f'Writing new tweets for {username}...')
				csv_df = pd.read_csv(csv_file_path, parse_dates=['date'])
				csv_df = csv_df.append(tweets_df, ignore_index = True) # append tweets to csv
				csv_df = csv_df.sort_values('date', ascending=False) # Sort csv by date
				csv_df.to_csv(csv_file_path, sep=',', index=False)
			else:
				tweets_df.to_csv(csv_file_path, sep=',', index=False)

		# Else: there were no new tweets pulled.
		else:
			logger.debug(f"Scraping #{scraping_counter}/{number_of_users}, {username}: No new tweets. CSV was not updated, and no JSON file created.")

		# Update this user's record in record_csv to show we just scraped.
		record_csv.loc[index, 'last_scraped'] = now_as_string_for_record_csv
		record_csv.to_csv(RECORD_CSV_FILE_PATH, sep=',', index=False)

		logger.info(f'Done scraping #{scraping_counter}/{number_of_users}: {username}')

	logger.info(f'Done Twitter scraping for all users')

# Download images and videos on posts
def download_media(record_csv):
	logger.info('Start Twitter media download')

	number_of_users = len(record_csv)
	media_user_counter = 0

	# For every account in record_csv, download its Twitter media (images and csv).
	for index, row in record_csv.iterrows():
		media_user_counter += 1
		username = row['account']

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

				if item['_type'] == 'snscrape.modules.twitter.Video':
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
					video_counter += 1

				# Extract photo
				elif item['_type'] == 'snscrape.modules.twitter.Photo':
					urls_to_download.append([item['fullUrl'],'photo'])
					logger.debug(f'Found photo #{photo_counter} URL in json file: ' + item['fullUrl'])
					photo_counter += 1

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
				logger.info(f'Media download, user #{media_user_counter}/{number_of_users}, {username}: {download_counter}/{total_video_and_photo} ({url}) already downloaded!')
				continue

			path = urlparse(url).path
		
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

# Run script 
# ================================================
if __name__ == '__main__':
	# Initialize argument parser
	parser = argparse.ArgumentParser()
	# Required argument
	parser.add_argument("-s", "--savelocation", dest="SAVE_FOLDER", help="Save location for Twitter backup", required=True)
	# Optional argument
	parser.add_argument("-r", "--record_csv_file_path", dest="RECORD_CSV_FILE_PATH", help="File path to CSV containing list of Twitter users to scrape (see README)", default="twitter_user_record_list.csv")
	# Optional argument
	parser.add_argument("-d", "--debug", dest="DEBUG_MODE",
						action="store_true", default=False, help="Print debug messages")

	args = parser.parse_args()

	SAVE_FOLDER = args.SAVE_FOLDER
	RECORD_CSV_FILE_PATH = args.RECORD_CSV_FILE_PATH
	DEBUG_MODE = args.DEBUG_MODE


	# Logging
	# =================================================
	logger = logging.getLogger(__name__)
	if DEBUG_MODE is True:
		logger.setLevel(logging.DEBUG)
	else:
		logger.setLevel(logging.INFO)
	logger.debug(sys.argv)
	formatter = logging.Formatter('%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s')

	# Logging to stdout
	stream_handler = logging.StreamHandler()
	stream_handler.setLevel(logging.DEBUG)
	logger.addHandler(stream_handler)
	stream_handler.setFormatter(formatter)

	now_datetime = datetime.now().astimezone()
	now_as_string = now_datetime.strftime('%Y-%m-%d_%H%M')
	now_as_string_for_record_csv = now_datetime.strftime('%Y-%m-%d %H:%M:%S %z')

	# Main script
	record_csv = open_record_csv(RECORD_CSV_FILE_PATH)
	scrape_posts(record_csv)
	download_media(record_csv)
