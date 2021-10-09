'''
# Download Facebook post's images and videos
# This script will download all the images and videos of all posts inside a given JSON file 
# Last updated: 2021-10-08
'''

import logging, os, urllib.parse, urllib.request, socket
from datetime import datetime
from urllib.request import HTTPError

import pandas as pd, emoji

from facebook_scraper import *
from progressist import ProgressBar

# ============================================
# Helper functions
def get_input_variables():
	while True:
		try:
			username = input("Enter username of FB profile you want to download:\n")
			if username == '':
				print('You did not enter a username! Try again!')
				continue

			json_file_path = input("\nEnter path to JSON file containing posts. Your JSON file MUST have been pulled within 12-24 hours of running this script (otherwise downloading will not work).\n(Ex: C:/users/hk/Desktop/fb_posts_standnews_20210614_0435.txt\nThis JSON file is generated by facebook_post_scraper.py file. Script will download all the images and videos, of the posts contained in JSON file.\n")
			if json_file_path == '':
				print('You did not enter a JSON file path! Try again!')
				continue

			# debug mode
			DEBUG_MODE = input("\nPrint debugging statements on screen? Y for yes, or N for no: \n")
			if DEBUG_MODE.lower() != 'y' and DEBUG_MODE.lower() != 'n':
				print("Invalid input! Only Y or N is accepted. Try again!")
				continue
			if DEBUG_MODE.lower() == 'y':
				DEBUG_MODE = True
			elif DEBUG_MODE.lower() == 'n':
				DEBUG_MODE = False

		except ValueError as e:
			print("Invalid input! Try again!")
			continue

		return_dict = {
			'username': username,
			'json_file_path': json_file_path,
			'DEBUG_MODE': DEBUG_MODE
		}
		return return_dict 

# Create the name of folder to store posts in
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

# If a post contains a video, get its URL
def get_video_url(post):
	# Dict key is "image id", Dict Value is "image url"
	video_url_dict = {}

	if post['video'] is not None and post['video'].startswith('https://'):
		video_id = post['video_id']
		video_url_dict[video_id] = post['video']
		return video_url_dict
	else:
		return False

# Get the post's image URLs, if any
def get_images_urls(post):
	# Dict key is "image id", Dict Value is "image url"
	image_urls_dict = {}

	if 'image_ids' in post:
		if post['image_ids'] is not None:
			if len(post['image_ids']) >= 1:
				img_counter = 0

				for image_id in post['image_ids']:
					image_url = post['images'][img_counter]
					img_counter += 1
					image_urls_dict[image_id] = image_url

				return image_urls_dict
	
	return False

# Get the post's low quality image URLs, if any
def get_low_quality_images_urls(post):
	# Dict key is "image id", Dict Value is "image url"
	low_quality_img_urls_dict = {}

	if len(post['images_lowquality']) >= 1:
		for img_lowquality_url in post['images_lowquality']:
			path = urllib.parse.urlparse(img_lowquality_url).path
			# Get file extension of url, from here: https://stackoverflow.com/a/4776959
			ext = os.path.splitext(path)[1]

			img_id = path.rsplit("/", 1)[-1]
			img_id = img_id.replace(ext,'') # replace extra extension in img_id

			low_quality_img_urls_dict[img_id] = img_lowquality_url
		return low_quality_img_urls_dict
	return False

def populate_record_csv(json_obj, record_df):
	global number_of_videos
	global number_of_images
	global number_of_images_low_quality

	post_number = 0

	# Go through post JSOn object, extract video / image URLs, add to record CSV 
	for post in json_obj:
		post_number += 1

		# Add video URLs
		video_url_dict = get_video_url(post)

		if video_url_dict is not False:
			[(video_id, video_url)] = video_url_dict.items() # Each video can have only 1 video. Key is the video_id, value is video_url.
			number_of_videos += 1

			if video_id not in record_df['media_id'].values:
				record_df = record_df.append(
					{'post_number': post_number,
					'media_id': video_id,
					'url': video_url, 
					'type': 'video',
					'post_id': post['post_id'], 
					'post_text': post['text'], 
					'post_date': post['time'],
					'status': 'pending'
					}, ignore_index=True)

		# Add image URLs
		image_urls_dict = get_images_urls(post)

		if image_urls_dict is not False:
			number_of_images += len(image_urls_dict)

			for image_id, url in image_urls_dict.items():

				# Note: record_df['post_id'] is an int
				check_if_row_exists_result = ((record_df['url'] == url) & (record_df['type'] == 'image') & (record_df['media_id'] == image_id) & (record_df['post_id'] == int(post['post_id']))).any()

				# Check if a row with this URL, post_id, and media_id exists
				if check_if_row_exists_result == False:

					record_df = record_df.append(
						{'post_number': post_number,
						'media_id': image_id,
						'url': url, 
						'type': 'image',
						'post_id': post['post_id'], 
						'post_text': post['text'], 
						'post_date': post['time'],
						'status': 'pending'
						}, ignore_index=True)

		# Add low quality image URLs
		low_quality_images_dict = get_low_quality_images_urls(post)

		if low_quality_images_dict is not False:
			number_of_images_low_quality += len(low_quality_images_dict)

			for image_id, url in low_quality_images_dict.items():

				# Note: record_df['post_id'] is an int
				check_if_row_exists_result = ((record_df['url'] == url) & (record_df['type'] == 'image_low_quality') & (record_df['media_id'] == image_id) & (record_df['post_id'] == int(post['post_id']))).any()

				if check_if_row_exists_result == False:

					record_df = record_df.append(
						{'post_number': post_number,
						'media_id': image_id,
						'url': url, 
						'type': 'image_low_quality',
						'post_id': post['post_id'], 
						'post_text': post['text'], 
						'post_date': post['time'],
						'status': 'pending'
						}, ignore_index=True)
	
	return record_df


def media_download(username, JSON_FILE_PATH):
	global number_of_videos
	global number_of_images
	global number_of_images_low_quality

	total_number_of_posts = 0
	number_of_videos = 0
	number_of_videos_downloaded = 0
	number_of_images = 0
	number_of_images_downloaded = 0
	number_of_images_low_quality = 0
	number_of_images_low_quality_downloaded = 0

	# load JSON file containing all posts for this user
	try:
		with open(JSON_FILE_PATH) as f:
			json_obj = json.load(f)
	except FileNotFoundError as e:
		logger.critical('JSON file not found! Did you enter the right file path? Exiting script!')
		sys.exit()

	# Create "media" folder if it does not exist
	if not os.path.exists(f'posts/{username}/media'):
		os.makedirs(f'posts/{username}/media')

	# set urllib browser header
	opener = urllib.request.build_opener()
	opener.addheaders = [('User-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:92.0) Gecko/20100101 Firefox/92.0')]
	urllib.request.install_opener(opener)

	# set socket timeout
	socket_timeout_secs = 60
	socket.setdefaulttimeout(socket_timeout_secs)

	post_counter = 0
	total_number_of_posts = len(json_obj)

	# Get all photo and video URLs first to create the CSV record file
	# =================================================================
	logger.info('Start preprocessing posts...')

	# Create CSV record file
	CSV_RECORD_FILE_PATH = f'posts/{username}/media/{username}_media_download_record.csv'

	if os.path.isfile(CSV_RECORD_FILE_PATH):
		record_df = pd.read_csv(CSV_RECORD_FILE_PATH, index_col=False)
	else:
		record_df = pd.DataFrame(columns=['post_number','media_id','url','status','type','post_id','post_text','post_date'])

	record_df = populate_record_csv(json_obj, record_df) 
	record_df['post_id'] = record_df['post_id'].astype('int')
	record_df.to_csv(CSV_RECORD_FILE_PATH, index=False)

	logger.info('Finish preprocessing posts')

	# Download images and videos
	# ============================================================
	for post in json_obj:
		post_id = post['post_id']

		post_counter += 1
		media_exists = False
		logger.info(f'Processing post #{post_counter}/{total_number_of_posts} - Post ID: {post_id} - Date: {post["time"]}')

		# Save files in its own folder
		# ==========================
		# replace ":" character in timezone offset, so that strptime can interpret time correctly
		if ":" == post["time"][-3:-2]:
			post_time_as_text = post["time"][:-3] + post["time"][-2:]

		post_time_as_text = datetime.strptime(post_time_as_text, "%Y-%m-%d %H:%M:%S%z").strftime('%Y%m%d_%H%M')
		# We don't want folder name to have emojis or newlines
		POST_SAVE_FOLDER_PATH = f'posts/{username}/media/{post_time_as_text}_{post_id}_{create_post_folder_name(post["text"],50)}'

		if not os.path.exists(POST_SAVE_FOLDER_PATH):
			os.makedirs(POST_SAVE_FOLDER_PATH)

		# If video exists, download video
		# ==========================================================
		video_url_dict = get_video_url(post)

		if video_url_dict is not False:
			media_exists = True

			video_id = list(video_url_dict.keys())[0]
			video_url = list(video_url_dict.values())[0]

			# If video has not been downloaded, then download it
			vid_downloaded_already_result = ((record_df['url'] == video_url) & (record_df['type'] == 'video') & (record_df['media_id'] == video_id) & (record_df['post_id'] == int(post_id)))
			
			if vid_downloaded_already_result.values[0] != 'ok':
				# Get file extension of url, from here: https://stackoverflow.com/a/4776959
				path = urllib.parse.urlparse(video_url).path
				ext = os.path.splitext(path)[1]

				# Download video
				bar = ProgressBar(template="Download |{animation}| {done:B}/{total:B} {percent} {elapsed} {tta} ")
				logger.info(f'Downloading post #{post_counter}/{total_number_of_posts}, video {video_id}...')
				logger.debug(video_url)

				try:
					urllib.request.urlretrieve(video_url, f'{POST_SAVE_FOLDER_PATH}/{post_id}_{video_id}{ext}', bar.on_urlretrieve)
					record_df.loc[record_df['url'] == video_url, 'status'] = 'ok'	
					number_of_videos_downloaded += 1			

				except TimeoutError as e:
					logger.error(f'Cannot download video. Post #{post_counter}/{total_number_of_posts}, Post ID: {post_id}. Video ID: {video_id}\nError: Timeout error ({socket_timeout_secs} s): {str(e)}')
					record_df.loc[record_df['url'] == video_url, 'status'] = 'error'				

				except HTTPError as e:
					logger.error(f'Cannot download video. Post #{post_counter}/{total_number_of_posts}, Post ID: {post_id}. Video ID: {video_id}\nHTTP Error: {str(e)}')
					record_df.loc[record_df['url'] == video_url, 'status'] = 'error'				

				except Exception as e: 
					logger.error(f'Cannot download video. Post #{post_counter}/{total_number_of_posts}, Post ID: {post_id}. Video ID: {video_id}\nError: {str(e)}')
					record_df.loc[record_df['url'] == video_url, 'status'] = 'error'				

			# Video has been downloaded, skip
			else:
				logger.info(f'Already downloaded, skipping: post #{post_counter}/{total_number_of_posts}, video {video_id}')
				logger.debug(video_url)

		# If this post contains images, then download them. 
		# ===========================================================
		# Check if "image_ids" json key exists
		img_and_low_quality_img_counter = 0

		image_urls_dict = get_images_urls(post)
		
		if image_urls_dict is not False:
			media_exists = True

			for image_id, image_url in image_urls_dict.items():

				img_and_low_quality_img_counter += 1

				# If image has not been downloaded, then download it
				img_downloaded_already_result = ((record_df['url'] == image_url) & (record_df['type'] == 'image') & (record_df['media_id'] == image_id) & (record_df['post_id'] == int(post['post_id'])))

				if img_downloaded_already_result.values[0] != 'ok':

					logger.info(f'Downloading post #{post_counter}/{total_number_of_posts}, image #{img_and_low_quality_img_counter}, image id: {image_id}...')
					logger.debug(image_url)

					# Get file extension of url, from here: https://stackoverflow.com/a/4776959
					path = urllib.parse.urlparse(image_url).path
					ext = os.path.splitext(path)[1]

					try:
						urllib.request.urlretrieve(image_url, f'{POST_SAVE_FOLDER_PATH}/{post_id}_{img_and_low_quality_img_counter:02d}_{image_id}{ext}')
						record_df.loc[record_df['url'] == image_url, 'status'] = 'ok'	
						number_of_images_downloaded += 1			
						
					except TimeoutError as e:
						logger.error(f'Cannot download image. Post #{post_counter}/{total_number_of_posts}, post ID: {post_id}, image #{img_and_low_quality_img_counter}, image ID: {image_id}\nError: Timeout error ({socket_timeout_secs} s): {str(e)}')
						record_df.loc[record_df['url'] == image_url, 'status'] = 'error'				

					except HTTPError as e:
						logger.error(f'Cannot download image. Post #{post_counter}/{total_number_of_posts}, post ID: {post_id}, image #{img_and_low_quality_img_counter}, image ID: {image_id}\nError code: {str(e.code)}\nHTTP Error: {str(e)}')
						record_df.loc[record_df['url'] == image_url, 'status'] = 'error'				

					except Exception as e:
						logger.error(f'Cannot download image. Post #{post_counter}/{total_number_of_posts}, post ID: {post_id}, image #{img_and_low_quality_img_counter}, image ID: {image_id}\nError: {str(e)}')
						record_df.loc[record_df['url'] == image_url, 'status'] = 'error'				

				# Image has been downloaded, skip
				else:
					logger.info(f'Already downloaded, skipping: post #{post_counter}/{total_number_of_posts}, image #{img_and_low_quality_img_counter}, image id: {image_id}...')
					logger.debug(image_url)


		# Download low quality images:
		# ======================================================
		low_quality_images_dict = get_low_quality_images_urls(post)

		if low_quality_images_dict is not False:
			media_exists = True

			for img_id, img_lowquality_url in low_quality_images_dict.items():
				
				img_and_low_quality_img_counter += 1

				# If this img id has not been downloaded, then download.
				img_lowquality_downloaded_already_result = ((record_df['url'] == img_lowquality_url) & (record_df['type'] == 'image_lowquality') & (record_df['media_id'] == img_id) & (record_df['post_id'] == int(post['post_id'])))
				
				if img_lowquality_downloaded_already_result.values[0] != 'ok':

					logger.info(f'Downloading post #{post_counter}/{total_number_of_posts}, image #{img_and_low_quality_img_counter}, image id: {img_id}...')
					logger.debug(img_lowquality_url)

					path = urllib.parse.urlparse(img_lowquality_url).path
					# Get file extension of url, from here: https://stackoverflow.com/a/4776959
					ext = os.path.splitext(path)[1]

					try:						
						urllib.request.urlretrieve(img_lowquality_url, f'{POST_SAVE_FOLDER_PATH}/{post_id}_{img_and_low_quality_img_counter:02d}_{img_id}{ext}')
						record_df.loc[record_df['url'] == img_lowquality_url, 'status'] = 'ok'	
						number_of_images_low_quality_downloaded += 1			

					except TimeoutError as e:
						logger.error(f'Cannot download image. Post #{post_counter}/{total_number_of_posts}, post ID: {post_id}, image #{img_and_low_quality_img_counter}, Low quality img ID: {img_id}\nError: Timeout error ({socket_timeout_secs} s): {str(e)}')
						record_df.loc[record_df['url'] == img_lowquality_url, 'status'] = 'error'			

					except HTTPError as e:
						logger.error(f'Cannot download image. Post #{post_counter}/{total_number_of_posts}, post ID: {post_id}, image #{img_and_low_quality_img_counter}, Low quality img ID: {img_id}\nError code: {str(e.code)}\nHTTP Error: {str(e)}')
						record_df.loc[record_df['url'] == img_lowquality_url, 'status'] = 'error'				
					except Exception as e:
						logger.error(f'Cannot download image. Post #{post_counter}/{total_number_of_posts}, post ID: {post_id}, image #{img_and_low_quality_img_counter}, Low quality img ID: {img_id}\nError: {str(e)}')
						record_df.loc[record_df['url'] == img_lowquality_url, 'status'] = 'error'				

				# Already downloaded, skip downloading
				else:
					logger.info(f'Already downloaded, skipping: post #{post_counter}/{total_number_of_posts}, image #{img_and_low_quality_img_counter}, image id: {img_id}...')
					logger.debug(img_lowquality_url)


		if media_exists == False:
			logger.info(f"No media for post #{post_id}")
			with open(f'{POST_SAVE_FOLDER_PATH}/no_media_for_this_post.txt','w') as f:
				# create empty file named "no_media_for_this_post.txt" to indicate that this post has no media
				pass
		
		record_df.to_csv(CSV_RECORD_FILE_PATH, index=False)

	return {
		'number_of_posts': total_number_of_posts,
		'number_of_videos': number_of_videos,
		'number_of_videos_downloaded': number_of_videos_downloaded,
		'number_of_images': number_of_images,
		'number_of_images_downloaded': number_of_images_downloaded,
		'number_of_images_low_quality': number_of_images_low_quality,
		'number_of_images_low_quality_downloaded': number_of_images_low_quality_downloaded
	}

# ============================================
# Run script
if __name__ == '__main__':

	# Set logging
	filename = os.path.basename(__file__)
	filename = filename.replace('.py','')
	stream_handler = logging.StreamHandler()

	logger = logging.getLogger()
	formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
	logger.addHandler(stream_handler)
	stream_handler.setFormatter(formatter)

	# Set up file logging
	now_as_string = datetime.now().strftime('%Y%m%d_%H%M')

	if not os.path.exists(f'logs/{filename}'):
		os.makedirs(f'logs/{filename}')
	file_handler = logging.FileHandler(f'logs/{filename}/{filename}_log_{now_as_string}.txt')
	file_handler.setLevel(logging.DEBUG)
	logger.addHandler(file_handler)
	file_handler.setFormatter(formatter)


	input_variables = get_input_variables()

	if input_variables['DEBUG_MODE'] == True:
		logger.setLevel(logging.DEBUG)
	else:
		logger.setLevel(logging.INFO)

	download_result = media_download(input_variables['username'], input_variables['json_file_path'])
