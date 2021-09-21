'''
# Scrape Facebook for posts
# Last updated: 2021-09-20
'''

import json, time, logging, os, argparse, traceback, requests
from datetime import datetime

import pandas as pd

from facebook_scraper import *

# PARAMETERS 
# ===================
COOKIES_FILE_DEFAULT_PATH = '' # set path to .json / .txt file
PROXY = '' # follow format: https://<username>:<password>@<ip address>:<port>' or https://<ip address>:port. HTTPS Proxies only.
post_counter = 0

# =======================
# Helper functions

# Get user input 
def get_input_variables():
	while True:
		try:
			user = input("Enter FB username of page to download:\n")
			if user == '':
				print("Username cannot be empty! Try again!")
				continue
			
			DOWNLOAD_ALL_POSTS = input("Download all posts? Y for Yes, N for No: (No means: script will only download new posts that have not been archived previously)\n")
			if DOWNLOAD_ALL_POSTS.lower() != 'y' and DOWNLOAD_ALL_POSTS.lower() != 'n':
				print("Invalid input! Only Y or N is accepted. Try again!")
				continue
			if DOWNLOAD_ALL_POSTS.lower() == 'y':
				DOWNLOAD_ALL_POSTS = True
			elif DOWNLOAD_ALL_POSTS.lower() == 'n':
				DOWNLOAD_ALL_POSTS = False


			start_url = input("\nEnter pagination link (if none, leave as blank and press ENTER). ONLY use if you are trying to resume a previous FB post pull AND have the pagination link, enter here. \nIf you don't know what a pagination link is, you don't need it. Leave as BLANK and press ENTER. See here for more info: https://github.com/kevinzg/facebook-scraper/issues/336#issuecomment-860289559\n")
			if start_url == '':
				start_url = None

			SAVE_FILE_PATH = input("\nEnter path to save posts in (leave blank for this folder):\n")

			# allow extra requests
			ALLOW_EXTRA_REQUESTS = input("\nAllow extra requests? Y for yes, or N for no. You should enter \"N\" unless you know what you are doing!\n(Allowing extra requests will get you temporarily banned from FB API much faster.)\n(See here for more info: https://github.com/kevinzg/facebook-scraper#optional-parameters\n")

			if ALLOW_EXTRA_REQUESTS.lower() != 'y' and ALLOW_EXTRA_REQUESTS.lower() != 'n':
				print("Invalid input! Only Y or N is accepted. Try again!")
				continue
			if ALLOW_EXTRA_REQUESTS.lower() == 'y':
				ALLOW_EXTRA_REQUESTS = True
			elif ALLOW_EXTRA_REQUESTS.lower() == 'n':
				ALLOW_EXTRA_REQUESTS = False

			# use cookies
			USE_COOKIES = input("\nUse FB account cookies? Y for yes, or N for no.\nIt is recommended to use cookies, as it is much less likely to be temporarily banned by FB.\nSee here for more info: https://github.com/kevinzg/facebook-scraper#optional-parameters\n")
	
			if USE_COOKIES.lower() != 'y' and USE_COOKIES.lower() != 'n':
				print("Invalid input! Only Y or N is accepted. Try again!")
				continue
			if USE_COOKIES.lower() == 'y':
				USE_COOKIES = True

				# cookies file path
				COOKIES_FILE_PATH = input("\nEnter full file path to FB account cookie file (should end in .json). Example: \"C:/users/hk/Desktop/fb_cookies.json\".\nLeave blank for default (set default in Python script). See here for instructions to get cookie file: https://github.com/kevinzg/facebook-scraper#optional-parameters\n")
			else:
				USE_COOKIES = False
				COOKIES_FILE_PATH = None


			# use proxy
			USE_PROXY = input("\nUse proxy? (If yes, update the PROXY variable in the script before running.) Y for yes, or N for no.\n")
			if USE_PROXY.lower() != 'y' and USE_PROXY.lower() != 'n':
				logger.info("Invalid input! Only Y or N is accepted. Try again!")
				continue
			if USE_PROXY.lower() == 'y':
				USE_PROXY = True
			elif USE_PROXY.lower() == 'n':
				USE_PROXY = False

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
			'username': user,
			'DOWNLOAD_ALL_POSTS': DOWNLOAD_ALL_POSTS,
			'SAVE_FILE_PATH': SAVE_FILE_PATH,
			'start_url': start_url,
			'ALLOW_EXTRA_REQUESTS': ALLOW_EXTRA_REQUESTS,
			'USE_COOKIES': USE_COOKIES,
			'COOKIES_FILE_PATH': COOKIES_FILE_PATH,
			'USE_PROXY': USE_PROXY,
			'DEBUG_MODE': DEBUG_MODE,
		}
		return return_dict 

# Read master archive file, to get the date we last pulled posts for a profile.
# (Ex: last time we pulled CNN FB page is 2021-01-03 18:33).
# (if DOWNLOAD_ALL_POSTS is True, return 1970-01-01 datetime, as we want to download all posts)
def read_archive_file(user, archive_file_path, CSV_FILE_PATH, DOWNLOAD_ALL_POSTS):
	blank_return_obj = {'last_crawl': datetime(1970, 1, 1, 0, 0, 0), 'newest_post_datetime': datetime(1970, 1, 1, 0, 0, 0), 'newest_post_id': None}

	csv_exists = True

	# If there is no existing CSV file containing this user's posts, return csv_exists = False
	if os.path.isfile(CSV_FILE_PATH) == False:
		csv_exists = False
		blank_return_obj['csv_exists'] = False
	else:
		blank_return_obj['csv_exists'] = True

	# If archive file does not exist, return an object that contains default/blank values.
	if os.path.isfile(archive_file_path) == False:
		return blank_return_obj
	elif DOWNLOAD_ALL_POSTS == True:
		return blank_return_obj

	while True:
		try:
			logger.debug('Accessing CSV archive file: ' + archive_file_path)
			archive_file_df = pd.read_csv(archive_file_path, index_col='user')
			break
		except Exception as e:
			logger.warning('Error accessing CSV archive file... retrying in 3 secs')
			time.sleep(3)
			continue

	if user not in archive_file_df.index:
		return blank_return_obj

	print('hi')
	return {
		'last_crawl': datetime.strptime(archive_file_df.loc[user, 'last_crawl'], '%Y-%m-%d %H:%M:%S %z'),
		'newest_post_datetime': datetime.strptime(archive_file_df.loc[user, 'newest_post_datetime'], '%Y-%m-%d %H:%M:%S %z'),
		'newest_post_id': archive_file_df.loc[user, 'newest_post_id'],
		'csv_exists': csv_exists,
	}

# Update master archive file to show we scraped a profile just now.
def update_archive_file(user, archive_file_path, newest_post_datetime = None, newest_post_id = None):
	logger.info(f'Updating archive file at {archive_file_path}...')

	if os.path.isfile(archive_file_path): # Check if the archive file exists

		# Read archive file
		while True:
			try:
				archive_file_df = pd.read_csv(archive_file_path, index_col=None)
				archive_file_df['newest_post_id'] = archive_file_df['newest_post_id'].astype(str)
				break
			except Exception as e:
				logger.warning('Error accessing CSV file... retrying in 3 secs')
				time.sleep(3)
				continue

		if user in archive_file_df['user'].values:
			# update last crawl with current time
			archive_file_df.loc[archive_file_df['user'] == user, ['last_crawl']] = datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %z')

			if newest_post_datetime is not None:
				archive_file_df.loc[archive_file_df['user'] == user, ['newest_post_datetime']] = newest_post_datetime.strftime('%Y-%m-%d %H:%M:%S %z')

			if newest_post_id is not None:
				archive_file_df.loc[archive_file_df['user'] == user, ['newest_post_id']] = newest_post_id

		else: 
			archive_file_df = archive_file_df.append({
				'user': user,
				'last_crawl': datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %z'),
				'newest_post_datetime': newest_post_datetime.strftime('%Y-%m-%d %H:%M:%S %z') if newest_post_datetime else None,
				'newest_post_id': str(newest_post_id) if newest_post_id is not None else None,
				}, ignore_index=True)

	else: # Archive file does not exist, create one.
		archive_file_df = pd.DataFrame(columns=['user','last_crawl', 'newest_post_datetime', 'newest_post_id'])
		archive_file_df = archive_file_df.append({
			'user': user,
			'last_crawl': datetime.now().strftime('%Y-%m-%d %H:%M:%S %z'),
			'newest_post_datetime': newest_post_datetime.strftime('%Y-%m-%d %H:%M:%S %z') if newest_post_datetime else None,
			'newest_post_id': str(newest_post_id) if newest_post_id is not None else None,
			}, ignore_index=True)


	archive_file_df.to_csv(archive_file_path, index=None)

# Write a csv file
def write_csv_file(df, csv_file_path):
	# if csv_file_path folder path does not exist, create folder
	if not os.path.exists(os.path.dirname(csv_file_path)): 
		os.makedirs(os.path.dirname(csv_file_path))

	logger.info('Writing csv')

	df.to_csv(csv_file_path,index=False)

# Write a json file
def write_json_file(posts, json_file_path):
	# if json file path folder path does not exist, create folder
	if not os.path.exists(os.path.dirname(json_file_path)):
		os.makedirs(os.path.dirname(json_file_path))

	logger.info('Writing json')

	with open(json_file_path, 'a') as f:
		f.write(json.dumps(posts, indent=4, sort_keys=True, default=str))
		f.write('\n')

# Pull facebook posts
def pull_facebook_posts(user, DOWNLOAD_ALL_POSTS, save_file_path, post_counter, options_dict, cookies_file=None, start_url=None, archive_file_path=None):

	if options_dict['allow_extra_requests'] == True:
		logger.warning(f'Allowing extra requests! You will get reactions for each post, BUT you will be temporarily banned by FB much faster!\nSee "extra_info" here: https://github.com/kevinzg/facebook-scraper#optional-parameters')

	# Only have one master csv file per user that stores posts, update this file as needed
	csv_file_path = f'{save_file_path}/posts/{username}/fb_posts_{user}.csv'

	json_file_path = f'{save_file_path}/posts/{username}/fb_posts_{user}_{now_as_string}.json'

	if os.path.isfile(csv_file_path):
		logger.debug(f'CSV File exists: {csv_file_path}')
		df = pd.read_csv(csv_file_path)
		df['time'] = pd.to_datetime(df['time'])
		# interpret all numeric values as integer, not a float
		# except for post_id as those may be very large
		df['post_id'] = df['post_id'].astype('str')
		df['likes'] = df['likes'].astype('Int64')
		df['comments'] = df['comments'].astype('Int64')
		df['shares'] = df['shares'].astype('Int64')
		df['reaction_count'] = df['reaction_count'].astype('Int64')
		df['video_duration_seconds'] = df['video_duration_seconds'].astype('Int64')
		df['video_height'] = df['video_height'].astype('Int64')
		# df['video_size_MB'] = df['video_size_MB'].astype('Int64')
		df['video_watches'] = df['video_watches'].astype('Int64')
		df['video_width'] = df['video_width'].astype('Int64')
		
	else:

		df = pd.DataFrame(columns=["post_id", "post_url", "time", "timestamp", "post_text", "likes", "comments", "shares", "fetched_time", "fetched_timestamp", "available", "reaction_count", "reactions", "comments_full","factcheck",\
			"image","image_id","image_ids","image_lowquality","images",\
			"images_description","images_lowquality","images_lowquality_description",\
			"is_live","link","reactors","shared_post_id","shared_post_url","shared_text",\
			"shared_time","shared_user_id","shared_username","shares","text",\
			"user_id","user_url","username","video","video_duration_seconds",\
			"video_height","video_id","video_quality","video_size_MB","video_thumbnail",\
			"video_watches","video_width","w3_fb_url","listing_location","listing_location","listing_price","listing_title"])

	temporary_banned_count = 0

	# if no archive_file_path was specified, then use default path (facebook_post_archive.csv)
	if archive_file_path == None:
		archive_file_path = 'facebook_post_archive.csv'

	# Get date of newest post pulled previously
	archive_file_record = read_archive_file(user, archive_file_path, csv_file_path, DOWNLOAD_ALL_POSTS)
	if archive_file_record['csv_exists'] == False:
		logger.info('CSV file does not exist! Downloading all posts mode enabled!')		
		DOWNLOAD_ALL_POSTS = True

	while True:
		try:
			if cookies_file:
				logger.info(f'Using cookies: {cookies_file}')
			else:
				logger.info('Not using cookies')

			# "post" is a JSON object representing 1 post.
			# This function grabs all posts from newest post on page (OR start_url if it is specified) to oldest post on page
			for post in get_posts(user,pages=50000,
										timeout=60,
										cookies=cookies_file,
										options=options_dict,
										start_url=start_url):

				post_counter += 1
				temporary_banned_count = 0 # reset temporary banned count

				logger.info(f'Pulled post #{post_counter}: {post["post_id"]}')

				# check if unix timestamp is returned. Getting unix timestamps are preferable but not mandatory.
				if post['timestamp'] is not None:
					post['time'] = datetime.fromtimestamp(post['timestamp']).astimezone()
				else:
					post['time'] = post['time'].astimezone()
					logger.debug(f'Post #{post_counter} ({post["post_id"]}) did not return a unix timestamp!')

				post['fetched_time'] = datetime.now().astimezone()
				post['fetched_timestamp'] = datetime.timestamp(datetime.now())

				# Show date of post if it exists
				try:
					logger.info(f'Post #{post_counter} date: {post["time"].strftime("%Y-%m-%d %H:%M:%S %z")}')
				except AttributeError as e:
					logger.info(f'Post #{post_counter} does not have a date!')


				# Check if post is earlier than the newest post pulled in the archive, if yes, stop pulling.
				# Only compare posts with unix timestamps to avoid any timezone related comparison issues.
				if post['timestamp'] is not None:
					# Look at first 10 posts to avoid any issues with pinned posts
					if post["timestamp"] < datetime.timestamp(archive_file_record['newest_post_datetime']) and post_counter > 10 and DOWNLOAD_ALL_POSTS == False: 
						logger.info(f'STOP pulling posts, as Post #{post_counter} ({post["post_id"]}, {post["time"].strftime("%Y-%m-%d %H:%M:%S %z")}) is older than newest_post_datetime ({archive_file_record["newest_post_datetime"].strftime("%Y-%m-%d %H:%M:%S %z")})')
						break

				# If never seen before, then add to CSV file and JSON file.
				if post['post_id'] not in df['post_id'].values:
					logger.debug('Never seen ' + str(post['post_id']) + ' before, new post')
					df = df.append(post, ignore_index=True)
					new_posts.append(post)
				# seen post before, but we want to download all posts, so we update existing row
				elif post['post_id'] in df['post_id'].values and DOWNLOAD_ALL_POSTS == True:
					# delete previously seen post, then readd
					df = df.loc[df['post_id'] != post['post_id']]
					df = df.append(post, ignore_index=True)
					new_posts.append(post)
					
			logger.info("Done pulling posts")

			newest_post = df['time'].max()
			oldest_post = df['time'].min()
			newest_post_id = df['post_id'][df['time'] == newest_post].astype(str).values[0]

			if len(new_posts) > 0:
				logger.info(f"{post_counter} posts ({len(new_posts)} new) retrieved in {round(time.time() - start)}s. Latest new post: {newest_post}. Oldest new post: {oldest_post}")
				update_archive_file(user, archive_file_path, newest_post, str(newest_post_id))

			else:
				logger.info(f"{post_counter} posts ({len(new_posts)} new) retrieved in {round(time.time() - start)}s.")
				update_archive_file(user, archive_file_path)

			write_csv_file(df, csv_file_path)
			write_json_file(new_posts, json_file_path)

			return new_posts

		except facebook_scraper.exceptions.TemporarilyBanned as e:
			temporary_banned_count += 1

			# Intentionally set a random number like "3476", "1177" to appear to not be a bot.
			sleep_secs = 3476 + (1177 * (temporary_banned_count - 1))
			logger.info(f"Temporarily banned, sleeping for {sleep_secs / 60} m ({sleep_secs} secs). Note: you will get temporary banned more often if you use EXTRA REQUESTS!")
			time.sleep(sleep_secs)

		except Exception as e:
			traceback.print_exc()
			if post_counter == 0:
				logger.error("No posts pulled due to error! Check if you entered FB username of the page you want to scrape, and cookie file path correctly!")
				logger.error('Error: ' + str(e))
				print(traceback.format_exc())
			else:
				newest_post = df['time'].max()
				oldest_post = df['time'].min()

				logger.error(f"Error! {post_counter} posts ({len(new_posts)} new) retrieved in {round(time.time() - start)}s. Newest post: {newest_post}. Oldest post: {oldest_post}")
				logger.error('Error: ' + str(e))
				write_csv_file(df, csv_file_path)
				write_json_file(new_posts, json_file_path)

			return new_posts

# =======================
# Initialize script

if __name__ == '__main__':

	# Initialize argument parser
	parser = argparse.ArgumentParser()
	parser.add_argument("-u", "--username", dest="username",
	                    help="FB username of page to download", metavar="FB_USERNAME")

	parser.add_argument("-da", "--download_all", dest="DOWNLOAD_ALL_POSTS",
						action="store_true", default=False,
	                    help="Download ALL posts, including posts previously archived before")

	# Optional
	parser.add_argument("-s", "--savelocation", dest="SAVE_FILE_PATH",
	                    help="Save location for FB posts", metavar="SAVE_FILE_PATH", default='')

	# Optional
	parser.add_argument("--start_url", dest="start_url",
						help="Start pagination URL (optional, used rarely, only when resuming a previous failed pull. If you don't know what this is, you don't need it.", default=None)

	# Optional
	parser.add_argument("-e", "--extra_requests", dest="ALLOW_EXTRA_REQUESTS", 
						action="store_true", default=False,
						help="Allow extra requests (to download all pages with photos, but increases chance of being\
						 temporarily banned by FB. Not recommended to use for most purposes.")
	# Optional
	parser.add_argument("--use_proxy",
	                    action="store_true", dest="USE_PROXY", default=False,
	                    help="Use proxy to download FB posts. Set proxy in \"PROXIES\" variable in this Python script.")

	# Optional
	parser.add_argument("--use_cookies",
	                    action="store_true", dest="USE_COOKIES", default=False,
	                    help="Use FB account cookie file, must set --cookies_file or -c")

	# Optional
	parser.add_argument("-c", "--cookies_file",
	                    action="store", dest="COOKIES_FILE_PATH", 
	                    help="Path to FB account cookie .txt file", metavar='COOKIES_FILE_PATH', default = None)

	# Optional
	parser.add_argument("-d", "--debug",
	                    action="store_true", dest="DEBUG_MODE", default=False,
	                    help="Print debug messages")

	args = parser.parse_args()
	if len(sys.argv) > 1:
		username = args.username
		DOWNLOAD_ALL_POSTS = args.DOWNLOAD_ALL_POSTS
		SAVE_FILE_PATH = args.SAVE_FILE_PATH
		start_url = args.start_url
		ALLOW_EXTRA_REQUESTS = args.ALLOW_EXTRA_REQUESTS
		USE_PROXY = args.USE_PROXY
		USE_COOKIES = args.USE_COOKIES
		COOKIES_FILE_PATH = args.COOKIES_FILE_PATH
		DEBUG_MODE = args.DEBUG_MODE

	elif len(sys.argv) == 1:
		input_variables = get_input_variables()
		username = input_variables['username']
		DOWNLOAD_ALL_POSTS = input_variables['DOWNLOAD_ALL_POSTS']
		SAVE_FILE_PATH = input_variables['SAVE_FILE_PATH']
		start_url = input_variables['start_url']
		ALLOW_EXTRA_REQUESTS = input_variables['ALLOW_EXTRA_REQUESTS']
		USE_PROXY = input_variables['USE_PROXY']
		USE_COOKIES = input_variables['USE_COOKIES']
		COOKIES_FILE_PATH = input_variables['COOKIES_FILE_PATH']
		DEBUG_MODE = input_variables['DEBUG_MODE']

	if SAVE_FILE_PATH == '':
		SAVE_FILE_PATH = os.getcwd()

	# ===============
	# Set up logging
	filename = os.path.basename(__file__)
	filename = filename.replace('.py','')

	logger = logging.getLogger(__name__)
	if DEBUG_MODE == True:
		logger.setLevel(logging.DEBUG)
	else:
		logger.setLevel(logging.INFO)

	formatter = logging.Formatter('%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s')

	now_as_string = datetime.now().strftime('%Y%m%d_%H%M')

	# Logging
	if not os.path.exists(f'logs/{filename}'): # create folder for logs
		os.makedirs(f'logs/{filename}')
	file_handler = logging.FileHandler(f'logs/{filename}/{filename}_log_{now_as_string}_{username}.txt')
	file_handler.setLevel(logging.DEBUG)
	logger.addHandler(file_handler)
	file_handler.setFormatter(formatter)

	stream_handler = logging.StreamHandler()
	logger.addHandler(stream_handler)
	stream_handler.setFormatter(formatter)

	# =============================
	# Run script
	global start
	start = time.time()
	new_posts = []

	OPTIONS_DICT = {
		"allow_extra_requests": ALLOW_EXTRA_REQUESTS,
		"posts_per_page": 10 if ALLOW_EXTRA_REQUESTS == True else 200,
	}

	proxies = { 'https' : PROXY } 

	# Set configs
	if DOWNLOAD_ALL_POSTS == True:
		logger.info('Downloading ALL posts, including posts archived previously!')

	if USE_PROXY == True:
		if PROXY == None or PROXY == '':
			logger.critical('Error! You want to use proxy, but did not specify a proxy! Edit the script first, and specify a proxy using the "PROXY" variable in the script! Exiting!')
			sys.exit()
		logger.info(f'Proxy being used! {PROXY}')
		r = requests.get('https://ifconfig.me', proxies=proxies, verify=False) 
		logger.info('Testing proxy IP address with https://ifconfig.me:')
		logger.info(r.text)
		
		set_proxy(PROXY) # Set PROXY for facebook-scraper (pull_facebook_posts function) 

	if USE_COOKIES == True:
		if COOKIES_FILE_PATH == '' or COOKIES_FILE_PATH == None:
			COOKIES_FILE_PATH = COOKIES_FILE_DEFAULT_PATH 
			if COOKIES_FILE_DEFAULT_PATH == '' or COOKIES_FILE_DEFAULT_PATH == None:
				logger.critical('Error! You want to use cookies, but did not specify a cookie file! You must set --cookies_file <path to cookies file> to use cookies, or set the path to a cookies file as the "COOKIES_FILE_DEFAULT_PATH" in the script! Exiting!')
				sys.exit()

	else:
		COOKIES_FILE_PATH = None

	if start_url != '' and start_url != None:
		logger.info(f'Start URL: {start_url}')

	if SAVE_FILE_PATH[-1] == '\\' or SAVE_FILE_PATH[-1] == '/':
		SAVE_FILE_PATH = SAVE_FILE_PATH[0:-1]

	time.sleep(3)

	ARCHIVE_FILE_PATH = 'facebook_post_archive.csv'

	# Pull FB posts
	pull_facebook_posts(username, DOWNLOAD_ALL_POSTS, SAVE_FILE_PATH, post_counter, OPTIONS_DICT, 
		COOKIES_FILE_PATH, start_url=start_url, archive_file_path=ARCHIVE_FILE_PATH)
