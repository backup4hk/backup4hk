# Download Instagram posts
# Last updated: 2021-10-03

# Instruction:
# 1. Go to "PARAMETERS" section below, follow COOKIES instructions
# 2. Run script without any arguments. When script is run, it'll ask you for the IG username you want to download, etc.

from datetime import datetime
import json, urllib.parse, logging, pandas as pd, os, sys, argparse, traceback, re

from ig_libraries import *
from split_multiple_json_in_txt_file import *

# ===================================================
# Parameters

# YOU NEED TO ADD YOUR COOKIE FOR YOUR IG ACCOUNT HERE.
# Instruction:
# 1. In your browser (Firefox or Chrome), log into instagram (recommend using a 太空 IG account)
# 2. Install extension to get IG cookie from browser.
# For chrome: install https://chrome.google.com/webstore/detail/editthiscookie/fngmhnnpilhplaeedifhccceomclgfbg?hl=en
# For Firefox: install https://addons.mozilla.org/en-US/firefox/addon/cookie-quick-manager/
# 3. Open the cookie extension. There should be the following IG cookies: [1] mid, [2] ig_did, [3] ig_nrcb, [4] csrftoken, [5] ds_user_id, [6] sessionid, [7] shbid, [8] shbts, [9] rur. (If there are additional cookies, you can ignore them).
# 4. For each of the above 9 cookies, copy and paste them below into the COOKIE variable, in this format:
# 'mid=<insert mid>; ig_did=<insert ig_did>; ig_nrcb=<insert ig_nrcb>; csrftoken=<insert csrf token>; ds_user_id=<insert ds_user_id>; sessionid=<insert sessionid>; shbid="<insert shbid>"; shbts="<insert shbts>"; rur="<insert rur>"'
# NOTE: you need to have double quotation "" surrounding the shbid, shbts, and rur values you insert.

# INSERT COOKIE HERE.
COOKIE = 'mid=<insert mid>; ig_did=<insert ig_did>; ig_nrcb=<insert ig_nrcb>; csrftoken=<insert csrf token>; ds_user_id=<insert ds_user_id>; sessionid=<insert sessionid>; shbid="<insert shbid>"; shbts="<insert shbts>"; rur="<insert rur>"'

HEADER_PAYLOAD = {
	"user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
	"accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
	"accept-encoding": "gzip, deflate, br",
	"cookie": COOKIE,
	"sec-ch-ua": '" Not;A Brand";v="99", "Google Chrome";v="91", "Chromium";v="91"',
	"sec-ch-ua-mobile": "?0",
	"sec-fetch-dest": "document",
	"sec-fetch-mode": "navigate",
	"sec-fetch-user": "?1",
	"upgrade-insecure-requests": "1",
}

#global PROXIES
PROXIES = {
	# Format: user:password@proxyserver:proxyport
	# "http": "http://myusername:password@164.235.3.53:18431"
	# "https": "http://myusername:password@164.235.3.53:18431"
}

QUERY_HASH = '56a7068fea504063273cc2120ffd54f3' #  pulled from internet


# Set waiting times
SECS_TO_WAIT_MIN = 1
SECS_TO_WAIT_MAX = 5
NUMBER_OF_PULLS_BEFORE_LONG_PULL = 15
MINS_TO_LONG_WAIT_MIN = 3
MINS_TO_LONG_WAIT_MAX = 6

WAITING_PARAMETERS = {
	'secs_to_wait_min': SECS_TO_WAIT_MIN,
	'secs_to_wait_max': SECS_TO_WAIT_MAX,
	'number_of_pulls_before_long_pull': NUMBER_OF_PULLS_BEFORE_LONG_PULL,
	'mins_to_long_wait_min': MINS_TO_LONG_WAIT_MIN,
	'mins_to_long_wait_max': MINS_TO_LONG_WAIT_MAX,
}

# ===================================================
# Helper functions
def remove_emoji_newline(text, num_characters_to_keep):
	regrex_pattern = re.compile(pattern = "["
		u"\U0001F600-\U0001F64F"  # emoticons
		u"\U0001F300-\U0001F5FF"  # symbols & pictographs
		u"\U0001F680-\U0001F6FF"  # transport & map symbols
		u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
		u"\n" # newline
							"]+", flags = re.UNICODE)
	stripped_text = regrex_pattern.sub(r'',text) [0:num_characters_to_keep]
	stripped_text = stripped_text.replace('/','')
	stripped_text = stripped_text.replace('\\','')

	return stripped_text

def get_input_variables():
	while True:
		try:
			mode = input("Input mode - 1 for all posts on profile, 2 for downloading all posts beyond an endcursor, 3 for single endcursor only:\n")

			if mode != '1' and mode != '2' and mode != '3':
				print('Invalid input! Try again!\n')
				continue

			if mode.lower() == '1':
				mode = 'all_posts_on_profile'
				username = input("Enter username of IG profile you want to download:\n")
				end_cursor = None
				userid = None

			elif mode.lower() == '2' or mode.lower() == '3':
				# Error checking on end_cursor
				end_cursor = input("Enter end_cursor:\n(it is 120 characters long, ending with \"==\")\n")
				if len(end_cursor) != 120:
					print("Invalid end_cursor! end_cursors are 120 characters long and end with \"==\". They frequently start with something similar to \"QVFE\").\n")
					continue

				username = input("Enter username:\n")
				txt_file_path = None

				if mode.lower() == 2:
					mode = 'beyond_end_cursor'
				elif mode.lower() == 3:
					mode = 'single_end_cursor'

			# Use proxy
			use_proxy = input("Use proxy? Y or N. If yes, specify proxy in script before proceeding.\n")
			if use_proxy.lower() != 'y' and use_proxy.lower() != 'n':
				print("Invalid input! Try again!\n")
				continue

			if use_proxy.lower() == 'y':
				use_proxy = True
			else:
				use_proxy = False

			# Save location
			SAVE_FILE_PATH = input("Enter save file path. Leave blank to save in this folder. Example: C:/users/hk/Desktop/backup/)\n")
			if SAVE_FILE_PATH == '':
				SAVE_FILE_PATH = os.getcwd()
			if SAVE_FILE_PATH[-1] == '\\' or SAVE_FILE_PATH[-1] == '/':
				SAVE_FILE_PATH = SAVE_FILE_PATH[0:-1]

			# Debug mode
			debug_mode = input("Use debug mode, to see debugging info? Y or N.\n")
			if debug_mode.lower() != 'y' and debug_mode.lower() != 'n':
				print("Invalid input! Try again!\n")
				continue

			if debug_mode.lower() == 'y':
				debug_mode = True
			else:
				debug_mode = False
		except ValueError as e:
			print("Invalid input! Try again!\n")
			continue

		return_dict = {
			'mode': mode.lower(),
			'end_cursor': end_cursor,
			'username': username,
			'use_proxy': use_proxy,
			'SAVE_FILE_PATH': SAVE_FILE_PATH,
			'DEBUG_MODE': debug_mode,
		}
		return return_dict # Return the mode (CSV or single profile) and the profile_file_path

def record_in_archive(filename, shortcode):
	with open(filename, 'a') as f:
		f.write(f'{shortcode}\n')
		f.close()
	return

def update_run_log(filename, username, now_dt_obj, mode, status):

	if os.path.isfile(filename):
		df_run_log = pd.read_csv(filename, index_col = None)

		if status == 'running':
			df_run_log = df_run_log.append({
				'username': username,
				'time': now_dt_obj.strftime('%Y-%m-%d %H:%M:%S'),
				'mode': mode,
				'status': status,
			}, ignore_index=True)
		else:
			df_run_log.loc[df_run_log['time'] == now_dt_obj.strftime('%Y-%m-%d %H:%M:%S'), ['status']] = status

	else:
		df_run_log = pd.DataFrame(columns=['username', 'time', 'mode', 'status'])

		if status == 'running':
			df_run_log = df_run_log.append({
				'username': username,
				'time': now_dt_obj.strftime('%Y-%m-%d %H:%M:%S'),
				'mode': mode,
				'status': status,
			}, ignore_index=True)

	df_run_log.to_csv(filename, index=False)

def update_run_log_by_user(filename, username, now_dt_obj, column_to_update):

	if os.path.isfile(filename):
		df_run_log_by_user = pd.read_csv(filename, index_col = None)

		if username in df_run_log_by_user['username'].values:
			df_run_log_by_user.loc[df_run_log_by_user['username'] == username, [column_to_update]] = now_dt_obj.strftime('%Y-%m-%d %H:%M')
		else:
			df_run_log_by_user = df_run_log_by_user.append({
				'username': username,
				column_to_update: now_dt_obj.strftime('%Y-%m-%d %H:%M'),
			}, ignore_index=True)

	else:
		df_run_log_by_user = pd.DataFrame(columns=['username', 'last_successful_pull_all_posts', 
			'last_successful_pull_any_posts', 'last_run'])
		df_run_log_by_user = df_run_log_by_user.append({
			'username': username,
			column_to_update: now_dt_obj.strftime('%Y-%m-%d %H:%M'),
			}, ignore_index=True)

	df_run_log_by_user.to_csv(filename, index=False)

def extract_posts_from_json(json_prefix):
	posts = []

	for item in json_prefix:
		node = item['node']

		# Get properties that exist for video and photo
		post_id = node['id']
		display_url = node['display_url']
		shortcode = node['shortcode']
		taken_at_unix_time = node['taken_at_timestamp']
		taken_at = datetime.fromtimestamp(taken_at_unix_time).strftime('%Y-%m-%d %H:%M %z')
		likes = node['edge_media_preview_like']['count']
		comments_count = node['edge_media_to_comment']['count']
		try:
			comments_count_more = node['edge_media_to_comment']['page_info']['has_next_page']
		except KeyError as e:
			comments_count_more = False
		owner_id = node['owner']['id']
		owner = node['owner']['username']
		try:
			caption = node['edge_media_to_caption']['edges'][0]['node']['text']
		except IndexError as e:
			caption = ''
		is_video = node['is_video']

		# See if this posts contain more than 1 photo/video
		# If yes, extract its photo/video URLs
		if 'edge_sidecar_to_children' in node:
			additional_media_url = []

			for media in node['edge_sidecar_to_children']['edges']:
				if media['node']['display_url'] != display_url:
					if media['node']['is_video'] == True:
						additional_media_url.append(media['node']['video_url'])
					else:
						additional_media_url.append(media['node']['display_url'])

			number_of_medias = len(node['edge_sidecar_to_children'])
		else:
			number_of_medias = 1
			additional_media_url = None

		post = {
			'json_post_metadata': node,
			'id': post_id,
			'display_url': display_url,
			'is_video': is_video,
			'video_url': None,
			'number_of_medias': number_of_medias,
			'additional_media_url': additional_media_url,
			'shortcode': shortcode,
			'taken_at': taken_at,
			'taken_at_unix_time': taken_at_unix_time,
			'likes': likes,
			'comments_count': comments_count,
			'comments_count_more': comments_count_more,
			'video_view_count': None,
			'video_duration': None,
			'caption': caption,
			'owner_id': owner_id,
			'owner': owner,
			'has_audio': None,
		}

		# Check if post is video, if yes, then extract more properties

		if is_video == True:
			has_audio = node['has_audio']
			video_url = node['video_url']
			video_view_count = node['video_view_count']
			try:
				video_duration = node['video_duration']
			except KeyError as e:
				video_duration = None

			post['has_audio'] = has_audio
			post['video_url'] = video_url
			post['video_view_count'] = video_view_count
			post['video_duration'] = video_duration

		# logger.debug(f'Processing {shortcode} - {datetime.fromtimestamp(taken_at).strftime('%Y-%m-%d %H:%M')}')

		posts.append(post)

	return posts

def get_userid(username, proxy=None):
	logger.debug(f"Getting userid for {username}")

	# Set API URL
	url_api = f'https://www.instagram.com/{username}/?__a=1'
	logger.debug(f'URL: {url_api}')

	json_obj = call_ig_api(url_api, HEADER_PAYLOAD, 'main_page_of_profile', proxy)

	# Get userid
	try:
		logging_page_id = json_obj['logging_page_id']
		userid = logging_page_id.replace('profilePage_', '')
		logger.info(f'User ID for {username}: {userid}')
		return userid
	except KeyError as e:
		logger.critical('Error: This username does not exist!')
		sys.exit()

def extract_userid_and_first_endcursor(json_obj):
	# Get userid
	try:
		logging_page_id = json_obj['logging_page_id']
		userid = logging_page_id.replace('profilePage_', '')
		logger.info(f'User ID for {username}: {userid}')
	except KeyError as e:
		logger.critical('Error: This username does not exist!')
		sys.exit()

	# NOTE: IGTV is a strict subset of Posts, therefore we can comment this out.	
	# Get end_cursor for IGTV
	# igtv_count = json_obj['graphql']['user']['edge_felix_video_timeline']['count']
	# if igtv_count > 0:
	# 	# Check if IGTV has a "next page", only if "next page" is True will there be a end_cursor.
	# 	igtv_has_next_page = json_obj['graphql']['user']['edge_felix_video_timeline']['page_info']['has_next_page']
	# 	if igtv_has_next_page == True or igtv_has_next_page == 'true':
	# 		igtv_end_cursor = json_obj['graphql']['user']['edge_felix_video_timeline']['page_info']['end_cursor']
	# 	else:
	# 		igtv_has_next_page = False
	# 		igtv_end_cursor = None 
	# else:
	# 	igtv_has_next_page = False
	# 	igtv_end_cursor = None

	# Get end_cursor for posts
	post_count = json_obj['graphql']['user']['edge_owner_to_timeline_media']['count']
	if post_count > 0:
		# Check if posts has a "next page", only if "next page" is True will there be a end_cursor.
		post_has_next_page = json_obj['graphql']['user']['edge_owner_to_timeline_media']['page_info']['has_next_page']
		if post_has_next_page == True or post_has_next_page == 'true':
			post_end_cursor = json_obj['graphql']['user']['edge_owner_to_timeline_media']['page_info']['end_cursor']
		else:
			post_has_next_page = False
			post_end_cursor = None 
	else:
		post_has_next_page = False
		post_has_next_page = False

	pulled_on = datetime.now().strftime('%Y-%m-%d %H:%M')
	return_dict = {
		'profile': username,
		'userid': userid,
		'pulled_on': pulled_on,
		# NOTE: IGTV is a strict subset of posts, so commenting out.
		# 'igtv_count': igtv_count,
		# 'igtv_has_next_page': igtv_has_next_page,
		# 'igtv_end_cursor': igtv_end_cursor,
		'post_count': post_count,
		'post_has_next_page': post_has_next_page,
		'post_end_cursor': post_end_cursor,
	}

	# print(json_obj)

	return return_dict

# mode = 'single' to get the posts from THIS endcursor only
# mode = 'all' get posts from ALL endcusors following this one, recursively
def get_post_ids_from_endcursor(end_cursor, query_hash, username, userid, call_counter, igtv=False, mode='single', proxies=None):
	global df
	global SAVE_FILE_PATH

	call_counter += 1
	logger.info(f'API call #{call_counter}')
	logger.info(f'End cursor: {end_cursor}')

	# Set API URL
	url_api = f'https://www.instagram.com/graphql/query/?query_hash={query_hash}&variables='
	url_api_variables = f'{{"id":"{userid}","first":50,"after":"{end_cursor}"}}'
	url_api_variables_encoded = urllib.parse.quote_plus(url_api_variables)
	url_api = url_api + url_api_variables_encoded
	logger.info(f'URL: {url_api}')

	# Timeout, then Call IG API
	timeout(WAITING_PARAMETERS)
	json_obj = call_ig_api(url_api, HEADER_PAYLOAD, 'end_cursor', PROXIES)

	# Write to JSON file 
	with open(f'{SAVE_FILE_PATH}/{username}/{username}_ig_posts_{now_as_string}.json', 'a') as f:
		json.dump(json_obj, f)

	# Get next page and end cursors 
	try:
		has_next_page = json_obj['data']['user']['edge_owner_to_timeline_media']['page_info']['has_next_page']
	except TypeError as e:
		logger.critical('Invalid end_cursor entered!\nend_cursors should be 120 characters long, and end with "==". Most of the time (but not always), they start with something similar to "QVFE".')
		sys.exit()

	end_cursor = json_obj['data']['user']['edge_owner_to_timeline_media']['page_info']['end_cursor']

	json_prefix = json_obj['data']['user']['edge_owner_to_timeline_media']['edges']

	posts = extract_posts_from_json(json_prefix)
	df = df.append(posts, ignore_index = True)
	df.to_csv(f'{SAVE_FILE_PATH}/{username}/{username}_ig_posts_{now_as_string}.csv')

	last_post_timestamp = datetime.fromtimestamp(posts[0]['taken_at_unix_time']).strftime('%Y-%m-%d %H:%M')
	first_post_timestamp = datetime.fromtimestamp(posts[-1]['taken_at_unix_time']).strftime('%Y-%m-%d %H:%M')
	if igtv is True:
		logger.debug(f'Processed {len(json_prefix)} IGTV posts: {first_post_timestamp} to {last_post_timestamp} ')
	else:
		logger.debug(f'Processed {len(json_prefix)} posts: {first_post_timestamp} to {last_post_timestamp} ')

	if has_next_page == False or mode == 'single': #or call_counter == 2: # For debugging --> or call_counter == 2:
		return posts
	else:
		new_list_of_posts = get_post_ids_from_endcursor(end_cursor, query_hash, username, userid, call_counter, igtv, 'all')
		posts  = posts + new_list_of_posts
		return posts

# recurisve = continue to keep pulling posts
def get_posts_on_first_page(username, header, waiting_parameters, recursive=False, proxies=None):

	global df
	global SAVE_FILE_PATH

	# Set URLs to call
	url_api = f'https://www.instagram.com/{username}/?__a=1'
	logger.debug(f'URL for main_profile_of_page API: {url_api}')

	# Wait
	timeout(waiting_parameters)

	# Call IG API
	json_obj = call_ig_api(url_api, header, 'main_page_of_profile', proxies)

	if not os.path.exists(f'{SAVE_FILE_PATH}/{username}'):
		os.makedirs(f'{SAVE_FILE_PATH}/{username}')
	
	with open(f'{SAVE_FILE_PATH}/{username}/{username}_ig_posts_{now_as_string}.json', 'a') as f:
		json.dump(json_obj, f)

	# Get userid and first endcursor
	userid_and_first_endcursor_dict = extract_userid_and_first_endcursor(json_obj)

	# NOTE: IGTV is a strict subset of posts, so commenting out.
	# Get IGTV posts for first page, if any
	# if userid_and_first_endcursor_dict['igtv_count'] > 0:
	# 	json_prefix_first_page_igtv = json_obj['graphql']['user']['edge_felix_video_timeline']['edges']
	# 	igtv_posts = extract_posts_from_json(json_prefix_first_page_igtv)

	# 	last_post_timestamp = datetime.fromtimestamp(igtv_posts[0]['taken_at_unix_time']).strftime('%Y-%m-%d %H:%M')
	# 	first_post_timestamp = datetime.fromtimestamp(igtv_posts[-1]['taken_at_unix_time']).strftime('%Y-%m-%d %H:%M')
	# 	logger.debug(f'Processed {len(igtv_posts)} IGTV posts: {first_post_timestamp} to {last_post_timestamp} ')
	# 	df = df.append(igtv_posts, ignore_index = True)
	# 	# Write to JSON file 
	# 		with open(f'posts/{username}/{username}_ig_posts_{now_as_string}.json', 'a') as f:
	# 		json.dump(json_obj, f)

	# else:
	# 	igtv_posts = None

	# Get posts for first page
	if userid_and_first_endcursor_dict['post_count'] > 0:
		json_prefix_first_page_posts = json_obj['graphql']['user']['edge_owner_to_timeline_media']['edges']
		posts = extract_posts_from_json(json_prefix_first_page_posts)

		last_post_timestamp = datetime.fromtimestamp(posts[0]['taken_at_unix_time']).strftime('%Y-%m-%d %H:%M')
		first_post_timestamp = datetime.fromtimestamp(posts[-1]['taken_at_unix_time']).strftime('%Y-%m-%d %H:%M')
		logger.debug(f'Processed {len(posts)} posts: {first_post_timestamp} to {last_post_timestamp} ')
		df = df.append(posts, ignore_index = True)
	else:
		posts = None

	df.to_csv(f'{SAVE_FILE_PATH}/{username}/{username}_ig_posts_{now_as_string}.csv')


	if recursive == True:
		userid = userid_and_first_endcursor_dict['userid']
		# print(userid)

		# NOTE: IGTV is a strict subset of posts, so commenting out.
		# # Get IGTV posts for next page
		# if userid_and_first_endcursor_dict['igtv_has_next_page'] == True:
		# 	igtv_end_cursor = userid_and_first_endcursor_dict['igtv_end_cursor']
		# 	igtv_posts.append(get_post_ids_from_endcursor(igtv_end_cursor, QUERY_HASH, 
		# 		username, userid, 1, igtv=True, mode='all'))

		if userid_and_first_endcursor_dict['post_has_next_page'] == True:
			post_end_cursor = userid_and_first_endcursor_dict['post_end_cursor']
			posts.append(get_post_ids_from_endcursor(post_end_cursor, QUERY_HASH, 
				username, userid, 1, igtv=False, mode='all'))

	return {
		'userid_and_first_endcursor_dict': userid_and_first_endcursor_dict,
		# NOTE: IGTV is a strict subset of posts, so commenting out.
		# 'igtv_posts': igtv_posts,
		'posts': posts,
	}

# Download the actual photos and videos
def download_media(username, archive_file_path, proxies=None):
	global df
	global SAVE_FILE_PATH

	logger.info('Begin downloading posts (function "download_media")')

	if os.path.isfile(archive_file_path):
		with open(archive_file_path, 'r') as f:
			already_downloaded_posts = f.readlines()
			f.close()
	else:
		already_downloaded_posts = []

	if not os.path.exists(SAVE_FILE_PATH + '/' + username + '/media'):
		os.makedirs(SAVE_FILE_PATH + '/' + username + '/media')

	post_counter = 0
	total_num_of_posts = len(df)

	if proxies != None:
		proxy = urllib.request.ProxyHandler(proxies)
		opener = urllib.request.build_opener(proxy)
		urllib.request.install_opener(opener)
		test_proxy_request = requests.get('https://www.ifconfig.me', proxies=proxies)
		logger.debug(f"Proxy test: Your IP address is seen as: {test_proxy_request.text}")


	for index, row in df.iterrows():
		media_counter_this_post = 0
		post_counter += 1
		
		shortcode = row['shortcode']
		taken_at_timestamp = datetime.fromtimestamp(row['taken_at_unix_time']).strftime('%Y-%m-%d %H:%M')
		if shortcode in already_downloaded_posts:
			logger.info(f'Already downloaded: post #{post_counter}/{total_num_of_posts}: {shortcode} - {taken_at_timestamp}')
			continue	

		try:
			urls_to_download = []
			if row['is_video'] == True:
				urls_to_download.append(row['video_url'])
			else:
				urls_to_download.append(row['display_url'])

			if row['additional_media_url'] is not None:
				urls_to_download = urls_to_download + row['additional_media_url']
			
			media_folder_name = datetime.fromtimestamp(row['taken_at_unix_time']).strftime('%Y%m%d_%H%M') + '_' + shortcode + '_' + remove_emoji_newline(row['caption'],50)

			if not os.path.exists(SAVE_FILE_PATH + '/' + username + '/media/' + media_folder_name):
				os.makedirs(SAVE_FILE_PATH + '/' + username + '/media/' + media_folder_name)

			for url in urls_to_download:
				media_counter_this_post += 1
				logger.info(f'Downloading post #{post_counter}/{total_num_of_posts}, media #{media_counter_this_post}/{len(urls_to_download)}: {shortcode} - {taken_at_timestamp}')

				# Get file extension of url, from here: https://stackoverflow.com/a/4776959
				path = urllib.parse.urlparse(url).path
				ext = os.path.splitext(path)[1]

				download_tries = 0

				while True:
					try:
						download_tries += 1
						urllib.request.urlretrieve(url, SAVE_FILE_PATH + '/' + username + '/media/' + media_folder_name + '/' + shortcode + '_' + str(media_counter_this_post) + ext)
						break
					except Exception as e:
						if download_tries < 3:
							logger.warning(f'Could not download post#{post_counter}/{total_num_of_posts}, media#{media_counter_this_post}/{len(urls_to_download)}: {url}')
							logger.warning(f'Will retry {3-download_tries} more times. Waiting 3 secs before retrying...')
							time.sleep(3)
						if download_tries >= 3:
							logger.error(f'Could not download post#{post_counter}/{total_num_of_posts}, media#{media_counter_this_post}/{len(urls_to_download)}: {url}')
							logger.error('Tried 3 times already! Skipping to next media!')
							break

			# For every folder, write a csv file that contains this post's metadata
			row.to_csv(SAVE_FILE_PATH + '/' + username + '/media/' + media_folder_name + '/' + shortcode + '_metadata.csv', header=False)

			record_in_archive(ARCHIVE_FILENAME, row['shortcode'])
		
		except Exception as e:
			logger.error(f'Failed to download media for post #{post_counter}/{total_num_of_posts}: {shortcode} - {taken_at_timestamp}')
			# logger.debug(e)
			print(traceback.format_exc())
			
# ===================================================
# Main script

# Initalize logging
filename = os.path.basename(__file__)
filename = filename.replace('.py','')

logger = logging.getLogger()
logger.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s')

now_dt_obj = datetime.now()
now_as_string = now_dt_obj.strftime('%Y%m%d_%H%M')

stream_handler = logging.StreamHandler()
logger.addHandler(stream_handler)
stream_handler.setFormatter(formatter)

# Run script
if __name__ == '__main__':
	try:
		global SAVE_FILE_PATH

		# Initialize argument parser
		parser = argparse.ArgumentParser()
		parser.add_argument("-u", "--username", dest="username",
		                    help="username of IG page to download", metavar="IG_USERNAME")
		parser.add_argument("--use_proxy",
		                    action="store_true", dest="USE_PROXY", default=False,
		                    help="Use proxy to download IG posts. Set proxy in \"PROXIES\" variable in this Python script.")
		parser.add_argument("--debug",
		                    action="store_true", dest="DEBUG_MODE", default=False,
		                    help="Print debug messages")
		parser.add_argument("--savelocation", dest="SAVE_FILE_PATH",
		                    help="Save location for IG posts", metavar="SAVE_FILE_PATH")
		parser.add_argument("--single_end_cursor",
		                    action="store", dest="single_end_cursor", default=False, metavar='END_CURSOR',
		                    help="Only download posts in this end_cursor [usually 50 posts]. Use like this: --single_end_cursor [INPUT END_CURSOR HERE]")
		parser.add_argument("--beyond_end_cursor",
		                    action="store", dest="beyond_end_cursor", default=False, metavar='END_CURSOR',
		                    help="Download posts, starting from this end cursor, to earliest post by this page. Use like this: --beyond_end_cursor [INPUT END_CURSOR HERE]")

		args = parser.parse_args()
		#print(args)

		if len(sys.argv) > 1:
			input_variables = {}
			if args.single_end_cursor is False and args.beyond_end_cursor is False:
				input_variables['mode'] = 'all_posts_on_profile'
			elif args.single_end_cursor is True and args.beyond_end_cursor is True:
				print("Error! You cannot specify both --single_end_cursor and --beyond_end_cursor! Must pick only one!")
				sys.exit()
			elif args.single_end_cursor is True and args.beyond_end_cursor is False:
				input_variables['mode'] = 'single_end_cursor'
				input_variables['end_cursor'] = args.single_end_cursor
			else:
				input_variables['mode'] = 'beyond_end_cursor'
				input_variables['end_cursor'] = args.beyond_end_cursor

			username = args.username
			USE_PROXY = args.USE_PROXY
			SAVE_FILE_PATH = args.SAVE_FILE_PATH
			DEBUG_MODE = args.DEBUG_MODE

		elif len(sys.argv) == 1:
			input_variables = get_input_variables()
			DEBUG_MODE = input_variables['DEBUG_MODE']
			username = input_variables['username']
			USE_PROXY = input_variables['use_proxy']
			SAVE_FILE_PATH = input_variables['SAVE_FILE_PATH']

		if DEBUG_MODE is True:
			logger.setLevel(logging.DEBUG)

		# update run log
		if not os.path.exists(f'logs/{filename}'):
			os.makedirs(f'logs/{filename}')
		run_log_by_ig_user_file_path = f'logs/{filename}/run_log_by_ig_user.csv'
		run_log_file_path = f'logs/{filename}/run_log.txt'
		update_run_log_by_user(run_log_by_ig_user_file_path, username, now_dt_obj, 'last_run')
		update_run_log(run_log_file_path, username, now_dt_obj, input_variables['mode'], 'running')

		logger.info('Pulling: ' + username)

		# Create file logging
		file_handler = logging.FileHandler(f'logs/{filename}/{filename}_log_{username}_{now_as_string}.txt')
		file_handler.setLevel(logging.DEBUG)
		logger.addHandler(file_handler)
		file_handler.setFormatter(formatter)

		# Declare global variables
		global ARCHIVE_FILENAME
		ARCHIVE_FILENAME = f'{SAVE_FILE_PATH}/{username}/{username}_ig_archive.txt'

		# this dataframe will store metadata of all IG posts
		global df
		df = pd.DataFrame(columns=['id','display_url','shortcode','is_video','video_url','number_of_medias','additional_media_url','taken_at','taken_at_unix_time','likes',
				'comments_count','comments_count_more','caption', 'owner_id','owner','video_view_count','video_duration','has_audio','json_post_metadata'])

		if USE_PROXY == False:
			PROXIES = None


	# Pull posts
		if input_variables['mode'] == 'all_posts_on_profile':
			returned_dict = get_posts_on_first_page(username, HEADER_PAYLOAD, WAITING_PARAMETERS, recursive=True, proxies=PROXIES)
			# igtv_posts = returned_dict['igtv_posts']
			posts = returned_dict['posts']
		
			update_run_log_by_user(run_log_by_ig_user_file_path, username, now_dt_obj, 'last_successful_pull_all_posts')
			update_run_log_by_user(run_log_by_ig_user_file_path, username, now_dt_obj, 'last_successful_pull_any_posts')

		elif input_variables['mode'] == 'beyond_end_cursor':
			end_cursor = input_variables['end_cursor']
			username = input_variables['username']
			userid = get_userid(username, PROXIES)

			logger.info(f'Getting all posts beyond end_cursor {end_cursor}')
			posts = get_post_ids_from_endcursor(end_cursor, QUERY_HASH, username, userid, 0, mode='all', proxies=PROXIES)

			update_run_log_by_user(run_log_by_ig_user_file_path, username, now_dt_obj, 'last_successful_pull_any_posts')

		elif input_variables['mode'] == 'single_end_cursor':
			end_cursor = input_variables['end_cursor']
			username = input_variables['username']
			userid = get_userid(username, PROXIES)

			logger.info(f'Getting all posts ONLY on end_cursor {end_cursor}')
			posts = get_post_ids_from_endcursor(end_cursor, QUERY_HASH, username, userid, 0, mode='single', proxies=PROXIES)

			update_run_log_by_user(run_log_by_ig_user_file_path, username, now_dt_obj, 'last_successful_pull_any_posts')

		download_media(username, ARCHIVE_FILENAME, PROXIES)
		update_run_log(run_log_file_path, username, now_dt_obj, input_variables['mode'], 'success')
		split_multiple_ig_jsons(f'{SAVE_FILE_PATH}/{username}/{username}_ig_posts_{now_as_string}.json')

	except Exception as e:
		logger.critical(f'Error! {e}')
		traceback.print_exc()
		update_run_log(run_log_file_path, username, now_dt_obj, input_variables['mode'], 'fail')

