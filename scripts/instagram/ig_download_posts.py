# Download Instagram posts
# Last updated: 2021-10-06

# Instruction:
# 1. Go to "PARAMETERS" section below, follow COOKIES instructions
# 2. Run script without any arguments. When script is run, it'll ask you for the IG username you want to download, etc.

from datetime import datetime
import json, urllib.parse, logging, pandas as pd, os, sys, argparse, traceback, re, ast
from time import strftime
import progressist

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

# Helper functions
# ===============================================================

# Write script state to a JSON file, for resuming this script later if needed
def script_state_record(state, phase, user, POST_CSV_FILE_PATH, SAVE_FOLDER_PATH, now_as_string, details_dict=None):

	if phase == '1-api':
		if details_dict.keys() != {"end_cursor"}:
			raise Exception('details_dict keys are incorrect, 1-api!')

	state_dict = {
		"state": state, # possible values: quit_by_user, error
		"phase": phase, # possible values: "1-api", "2-download"
		"user": user, # store IG username
		"POST_CSV_FILE_PATH": POST_CSV_FILE_PATH, # store CSV FILE PATH for posts
		"SAVE_FOLDER_PATH": SAVE_FOLDER_PATH,
		"script_start_time": now_as_string,
		"script_crash_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
		# optional_dict will contain:
		# For phase 1 - API: end_cursor
		# For phase 2 -  <we don't need to store anything, as we already have an ALREADY_DOWNLOADED_POST txt file, and can just resume download based on progress in that txt file)
		"details": details_dict, 
	}

	with open(RECORD_STATE_JSON_FILE_PATH, 'w') as f:
		json.dump(state_dict, f)

	return True

def script_state_delete():
	if os.path.exists(RECORD_STATE_JSON_FILE_PATH):
		os.remove(RECORD_STATE_JSON_FILE_PATH)

def script_state_check():
	if os.path.exists(RECORD_STATE_JSON_FILE_PATH):
		json_f = open(RECORD_STATE_JSON_FILE_PATH)
		state_dict = json.load(json_f)

		logger.info('Previous script run failed - found record state json file')

		while True:

			# Print details of previous script run
			print('')
			print('Your previous script run failed. Details:')
			print(f'Username: {state_dict["user"]}')
			if state_dict['phase'] == '1-api':
				print(f'Phase: 1/2 - Downloading post text and metadata from API')
			elif state_dict['phase'] == '2-download':
				print(f'Phase: 2/2 - Downloading post media files (photo, video)')
			else:
				logger.critical('Invalid phase in record state json file! Exiting!')
				sys.exit()
			print(f'CSV file of {state_dict["user"]}\'s posts: {state_dict["POST_CSV_FILE_PATH"]}')
			print(f'Folder to save {state_dict["user"]}\'s posts in: {state_dict["SAVE_FOLDER_PATH"]}')
			print(f'Script start time: {datetime.strptime(state_dict["script_start_time"], "%Y%m%d_%H%M").strftime("%Y-%m-%d %H:%M")}')
			print(f'Script crash time: {state_dict["script_crash_time"]}')
			print('')

			resume_run = input(f"Do you want to resume your last script run? Y for yes, N for No. If you enter N, you will have to repull {state_dict['user']}'s posts again from the beginning!\n").lower()

			if resume_run == 'y':
				USE_PROXY = input("Use proxy? Y or N. If yes, specify proxy in script before proceeding.\n").lower()

				if USE_PROXY == 'y':
					USE_PROXY = True
				elif USE_PROXY == 'n': 
					USE_PROXY = False
				else:
					print('You did not enter Y or N! Try again!')
					continue

				DEBUG_MODE = input("Use debug mode, to see debugging info? Y or N.\n").lower()

				if DEBUG_MODE == 'y':
					DEBUG_MODE = True
				elif DEBUG_MODE == 'n': 
					DEBUG_MODE = False
				else:
					print('You did not enter Y or N! Try again!')
					continue

				return {
					"state_json_exist": True,
					"resume_run": True,
					"USE_PROXY": USE_PROXY,
					"DEBUG_MODE": DEBUG_MODE,
					"username": state_dict["user"],
					"phase": state_dict["phase"],
					"POST_CSV_FILE_PATH": state_dict["POST_CSV_FILE_PATH"],
					"SAVE_FOLDER_PATH": state_dict["SAVE_FOLDER_PATH"],
					"now_as_string": state_dict['script_start_time'],
					"details": state_dict['details'],
				}

			elif resume_run == 'n':
				print('Not resuming previous script run!')
				return {
					"state_json_exist": True,
					"resume_run": False
				}			
			else:
				print('You did not enter Y or N! Try again!')
				continue

	return {
		"state_json_exist": False,
		"resume_run": False,
	}
	
def create_post_folder_name(text, max_num_characters_to_keep):
	# If post has no text, it will be a nan dataframe value
	if pd.isna(text):
		return ''

	regrex_pattern = re.compile(pattern = "["
		u"\U0001F600-\U0001F64F"  # emoticons
		u"\U0001F300-\U0001F5FF"  # symbols & pictographs
		u"\U0001F680-\U0001F6FF"  # transport & map symbols
		u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
		u"\n" # newline
							"]+", flags = re.UNICODE)
	stripped_text = regrex_pattern.sub(r'',text) [0:max_num_characters_to_keep]
	stripped_text = stripped_text.replace('/','')
	stripped_text = stripped_text.replace('\\','')
	stripped_text = stripped_text.replace(':','')
	stripped_text = stripped_text.replace('：','')
	stripped_text = stripped_text.replace('*','')
	stripped_text = stripped_text.replace('?','')
	stripped_text = stripped_text.replace('？','')
	stripped_text = stripped_text.replace('"','')
	stripped_text = stripped_text.replace('”','')
	stripped_text = stripped_text.replace('<','')
	stripped_text = stripped_text.replace('>','')
	stripped_text = stripped_text.replace('|','')

	while True:
		if len(stripped_text) == 0:
			break
		if stripped_text[-1] == ' ' or stripped_text[-1] == '.':
			stripped_text = stripped_text[:-1]
			continue
		break

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
			SAVE_FOLDER_PATH = input("Enter path to the folder you want to save IG posts in. Leave blank to save in this folder. Example: C:/users/hk/Desktop/backup/)\n")
			if SAVE_FOLDER_PATH == '':
				SAVE_FOLDER_PATH = os.getcwd()
			if SAVE_FOLDER_PATH[-1] == '\\' or SAVE_FOLDER_PATH[-1] == '/':
				SAVE_FOLDER_PATH = SAVE_FOLDER_PATH[0:-1]

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
			'SAVE_FOLDER_PATH': SAVE_FOLDER_PATH,
			'DEBUG_MODE': debug_mode,
		}
		return return_dict # Return the mode (CSV or single profile) and the profile_file_path

def record_in_already_downloaded_txt_file(TXT_FILE_PATH, shortcode):
	if os.path.isfile(TXT_FILE_PATH) == False:
		with open(TXT_FILE_PATH,'w') as f:
			f.write(f'{shortcode}\n')
		f.close()
	else:
		with open(TXT_FILE_PATH, 'r+') as f:
			found = False

			for line in f:
				if shortcode in line:
					found = True
			
			if found == False:
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
	global SAVE_FOLDER_PATH
	global POST_CSV_FILE_PATH 

	try:
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
		with open(f'{SAVE_FOLDER_PATH}/{username}/{username}_ig_posts_{now_as_string}.json', 'a') as f:
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
		df.to_csv(POST_CSV_FILE_PATH, index=False)

		last_post_timestamp = datetime.fromtimestamp(posts[0]['taken_at_unix_time']).strftime('%Y-%m-%d %H:%M')
		first_post_timestamp = datetime.fromtimestamp(posts[-1]['taken_at_unix_time']).strftime('%Y-%m-%d %H:%M')
		if igtv is True:
			logger.info(f'Scraped {len(json_prefix)} IGTV posts: {first_post_timestamp} to {last_post_timestamp} ')
		else:
			logger.info(f'Scraped {len(json_prefix)} posts: {first_post_timestamp} to {last_post_timestamp} ')

		if has_next_page == False or mode == 'single': #or call_counter == 2: # For debugging --> or call_counter == 2:
			return posts
		else:
			new_list_of_posts = get_post_ids_from_endcursor(end_cursor, query_hash, username, userid, call_counter, igtv, 'all')
			posts  = posts + new_list_of_posts
			return posts

	except Exception as e:
		script_state_record('error', '1-api', username, POST_CSV_FILE_PATH, now_as_string, SAVE_FOLDER_PATH, {'end_cursor': end_cursor, 'api_call_counter': call_counter})


# recurisve = continue to keep pulling posts
def get_posts_on_first_page(username, header, waiting_parameters, recursive=False, proxies=None):

	global df
	global SAVE_FOLDER_PATH

	# Set URLs to call
	url_api = f'https://www.instagram.com/{username}/?__a=1'
	logger.debug(f'URL for main_profile_of_page API: {url_api}')

	# Wait
	timeout(waiting_parameters)

	# Call IG API
	json_obj = call_ig_api(url_api, header, 'main_page_of_profile', proxies)

	if not os.path.exists(f'{SAVE_FOLDER_PATH}/{username}'):
		os.makedirs(f'{SAVE_FOLDER_PATH}/{username}')
	
	with open(f'{SAVE_FOLDER_PATH}/{username}/{username}_ig_posts_{now_as_string}.json', 'a') as f:
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
		logger.info(f'Scraped {len(posts)} posts: {first_post_timestamp} to {last_post_timestamp} ')
		df = df.append(posts, ignore_index = True)
	else:
		posts = None

	df.to_csv(f'{SAVE_FOLDER_PATH}/{username}/{username}_ig_posts_{now_as_string}.csv', index=False)


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
	global SAVE_FOLDER_PATH
	global POST_CSV_FILE_PATH

	logger.info('Begin downloading posts (function "download_media")')

	if os.path.isfile(archive_file_path):
		with open(archive_file_path, 'r') as f:
			already_downloaded_posts = [line.rstrip() for line in f]
			f.close()
	else:
		already_downloaded_posts = []

	if not os.path.exists(SAVE_FOLDER_PATH + '/' + username + '/media'):
		os.makedirs(SAVE_FOLDER_PATH + '/' + username + '/media')

	post_counter = 0
	total_num_of_posts = len(df)

	if proxies != None:
		proxy = urllib.request.ProxyHandler(proxies)
		opener = urllib.request.build_opener(proxy)
		urllib.request.install_opener(opener)
		test_proxy_request = requests.get('https://www.ifconfig.me', proxies=proxies)
		logger.debug(f"Proxy test: Your IP address is seen as: {test_proxy_request.text}")

	df['additional_media_url'] = df['additional_media_url'].astype(str)

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

			if row['additional_media_url'] != 'None':

				# additional media url is stored as a list, in literal string format, in the CSV (ex: ['https://1.com', 'https://222.com'])
				# So we need to interpret this string literally and turn it into list
				additional_media_url_list = ast.literal_eval(row['additional_media_url'])
				additional_media_url_list = [n.strip() for n in additional_media_url_list]
				urls_to_download = urls_to_download + additional_media_url_list
			
			media_folder_name = datetime.fromtimestamp(row['taken_at_unix_time']).strftime('%Y%m%d_%H%M') + '_' + shortcode + '_' + create_post_folder_name(row['caption'],50)

			if not os.path.exists(SAVE_FOLDER_PATH + '/' + username + '/media/' + media_folder_name):
				os.makedirs(SAVE_FOLDER_PATH + '/' + username + '/media/' + media_folder_name)

			for url in urls_to_download:
				media_counter_this_post += 1
				logger.info(f'Downloading post #{post_counter}/{total_num_of_posts}, media #{media_counter_this_post}/{len(urls_to_download)}: {shortcode} - {taken_at_timestamp}')

				# Get file extension of url, from here: https://stackoverflow.com/a/4776959
				path = urllib.parse.urlparse(url).path
				ext = os.path.splitext(path)[1]

				download_tries = 0

				bar = progressist.ProgressBar(template="Download |{animation}| {done:B}/{total:B} {percent} {elapsed} {tta} ")


				while True:
					try:
						download_tries += 1
						urllib.request.urlretrieve(url, SAVE_FOLDER_PATH + '/' + username + '/media/' + media_folder_name + '/' + shortcode + '_' + str(media_counter_this_post) + ext, bar.on_urlretrieve)
						break
					except Exception as e:
						if download_tries < 3:
							logger.warning(f'Could not download post #{post_counter}/{total_num_of_posts}, media#{media_counter_this_post}/{len(urls_to_download)}: {url}')
							logger.warning(f'Will retry {3-download_tries} more times. Waiting 5 secs before retrying...')
							time.sleep(5)
						if download_tries >= 3:
							logger.error(f'Failed to download post #{post_counter}/{total_num_of_posts}, media #{media_counter_this_post}/{len(urls_to_download)}: {url}')
							logger.error('Tried 3 times already! Skipping to next media!')
							break
						
			# For every folder, write a csv file that contains this post's metadata
			if os.path.exists(SAVE_FOLDER_PATH + '/' + username + '/media/' + media_folder_name) == False:
					os.makedirs(SAVE_FOLDER_PATH + '/' + username + '/media/' + media_folder_name)

			row.to_csv(SAVE_FOLDER_PATH + '/' + username + '/media/' + media_folder_name + '/' + shortcode + '_metadata.csv', header=False)

			record_in_already_downloaded_txt_file(ALREADY_DOWNLOADED_POST_TXT_PATH, shortcode)
		
		except Exception as e:
			logger.error(f'Failed to download media for post #{post_counter}/{total_num_of_posts}, media #{media_counter_this_post}/{len(urls_to_download)}: {shortcode} - {taken_at_timestamp}')
			# logger.debug(e)
			print(traceback.format_exc())

			script_state_record('error', '2-download', username, POST_CSV_FILE_PATH, SAVE_FOLDER_PATH, now_as_string)
	
			continue

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
		global SAVE_FOLDER_PATH
		global RECORD_STATE_JSON_FILE_PATH
		global POST_CSV_FILE_PATH

		RECORD_STATE_JSON_FILE_PATH = 'ig_download_posts_state.json'

		input_variables = {}

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
		parser.add_argument("--savelocation", dest="SAVE_FOLDER_PATH",
		                    help="Save location for IG posts", metavar="SAVE_FOLDER_PATH")
		parser.add_argument("--single_end_cursor",
		                    action="store", dest="single_end_cursor", default=False, metavar='END_CURSOR',
		                    help="Only download posts in this end_cursor [usually 50 posts]. Use like this: --single_end_cursor [INPUT END_CURSOR HERE]")
		parser.add_argument("--beyond_end_cursor",
		                    action="store", dest="beyond_end_cursor", default=False, metavar='END_CURSOR',
		                    help="Download posts, starting from this end cursor, to earliest post by this page. Use like this: --beyond_end_cursor [INPUT END_CURSOR HERE]")

		args = parser.parse_args()

		# Check if script state json exists, and whether user wants to resume script.
		resume_script_result = script_state_check()

		if resume_script_result['state_json_exist'] == True and resume_script_result["resume_run"] == True:
			RESUME_SCRIPT_RUN = True
			USE_PROXY = resume_script_result['USE_PROXY']
			DEBUG_MODE = resume_script_result['DEBUG_MODE']
			username = resume_script_result["username"]
			RESUME_PHASE = resume_script_result["phase"]
			POST_CSV_FILE_PATH = resume_script_result["POST_CSV_FILE_PATH"]
			SAVE_FOLDER_PATH = resume_script_result["SAVE_FOLDER_PATH"]
			now_as_string = resume_script_result['now_as_string']
			RESUME_DETAILS = resume_script_result['details']

			input_variables['mode'] = 'resume_script_run'

		# No state json file exists
		else:
			RESUME_SCRIPT_RUN = False
			if len(sys.argv) > 1:
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
				SAVE_FOLDER_PATH = args.SAVE_FOLDER_PATH
				DEBUG_MODE = args.DEBUG_MODE

			elif len(sys.argv) == 1:
				input_variables = get_input_variables()
				DEBUG_MODE = input_variables['DEBUG_MODE']
				username = input_variables['username']
				USE_PROXY = input_variables['use_proxy']
				SAVE_FOLDER_PATH = input_variables['SAVE_FOLDER_PATH']


			POST_CSV_FILE_PATH = f'{SAVE_FOLDER_PATH}/{username}/{username}_ig_posts_{now_as_string}.csv'

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
		global ALREADY_DOWNLOADED_POST_TXT_PATH
		ALREADY_DOWNLOADED_POST_TXT_PATH = f'{SAVE_FOLDER_PATH}/{username}/{username}_ig_already_downloaded_post.txt'

		# this dataframe will store metadata of all IG posts
		global df
		if RESUME_SCRIPT_RUN == True:
			df = pd.read_csv(POST_CSV_FILE_PATH, index_col=None)
		else:
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

		elif input_variables['mode'] == 'beyond_end_cursor' or (RESUME_SCRIPT_RUN == True and RESUME_PHASE == '1-api'):
			
			# If user entered end cursor
			if input_variables['mode'] == 'beyond_end_cursor':
				end_cursor = input_variables['end_cursor']
				username = input_variables['username']
				api_call_counter = 0
			# if user is resuming a run
			elif RESUME_SCRIPT_RUN == True and RESUME_PHASE == '1-api': 
				end_cursor = RESUME_DETAILS['end_cursor']
				api_call_counter = RESUME_DETAILS['api_call_counter']
				# no need to define username, as we already got this from checking resume_script_result 

			userid = get_userid(username, PROXIES)

			logger.info(f'Getting all posts beyond end_cursor {end_cursor}')
			posts = get_post_ids_from_endcursor(end_cursor, QUERY_HASH, username, userid, api_call_counter, mode='all', proxies=PROXIES)

			update_run_log_by_user(run_log_by_ig_user_file_path, username, now_dt_obj, 'last_successful_pull_any_posts')

		elif input_variables['mode'] == 'single_end_cursor':
			end_cursor = input_variables['end_cursor']
			username = input_variables['username']
			userid = get_userid(username, PROXIES)

			logger.info(f'Getting all posts ONLY on end_cursor {end_cursor}')
			posts = get_post_ids_from_endcursor(end_cursor, QUERY_HASH, username, userid, 0, mode='single', proxies=PROXIES)

			update_run_log_by_user(run_log_by_ig_user_file_path, username, now_dt_obj, 'last_successful_pull_any_posts')

		download_media(username, ALREADY_DOWNLOADED_POST_TXT_PATH, PROXIES)
		update_run_log(run_log_file_path, username, now_dt_obj, input_variables['mode'], 'success')
		try:
			json.loads(f'{SAVE_FOLDER_PATH}/{username}/{username}_ig_posts_{now_as_string}.json')
		except ValueError as e:
			split_multiple_ig_jsons(f'{SAVE_FOLDER_PATH}/{username}/{username}_ig_posts_{now_as_string}.json')

		# Check if state JSON file exists, if it does, then delete it, as we successfully ran this script.
		script_state_delete()

	except Exception as e:
		logger.critical(f'Error! {e}')
		traceback.print_exc()
		update_run_log(run_log_file_path, username, now_dt_obj, input_variables['mode'], 'fail')

