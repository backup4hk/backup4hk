'''
Download Facebook Videos, given a list of Facebook Video URLs
Read the README FIRST!
'''

# =========================================== 
# Importing libraries
from bs4 import BeautifulSoup, Tag
import requests, shutil, re, datetime, os, sys, logging, pandas as pd, argparse, traceback
from urllib.parse import urlparse
import urllib.request
from selenium import webdriver
from random import randint
from time import sleep
from progressist import ProgressBar
from datetime import datetime

# =============================================
# Helper function
def get_input_variables():
	while True:
		try:
			url_txt_file_path = input("Enter path to .txt file containing FB Video URLs:\nExample: C:\\users\\hk\\Desktop\\fb_vid_urls.txt\n")
			folder_file_path = input("\nEnter path to folder to save videos. Leave blank to use this folder.\nExample: C:\\users\\hk\\Documents\\backup\\\n")
			org_name = input("\nEnter organization name (used for filename):\nExample: thestandnews\n")
			fb_username = input("\nEnter username of FB page you are downloading:\nExample: standnewshk\n")
			chrome_profile_path = input("\nEnter path to Chrome profile folder. Leave blank to use default (this works for most people). \nMore info: https://www.howtogeek.com/255653/\nExample: C:\\users\\<yourusername>\\AppData\\Local\\Google\\Chrome\\User Data\n")
			chrome_profile_name = input("\nEnter Chrome profile name. \nExample: Profile 1\n")

			read_all = input("\nDownload all videos in Video URL .txt file? Y for Yes, N for No. ")
			if read_all.lower() != 'y' and read_all.lower() != 'n':
				print("You must enter Y or N!")
				continue
			elif read_all == 'y':
				start_line_num = None
				end_line_num = None
			elif read_all == 'n':
				start_line_num = input("\nEnter line number in .txt file to start downloading videos from.\nEx: 500 means start downloading at line 500.")
				end_line_num = input("\nEnter line number in .txt file to stop downloading videos at.\nEx: 750 means stop downloading at line 750.")

				try:
					int(start_line_num)
					int(end_line_num)
				except ValueError as e:
					print("Invalid number entered!")
					continue

			debug_mode = input("\nPrint debug statements? Y for Yes, N for No. ")
			if debug_mode.lower() != 'y' and debug_mode.lower() != 'n':
				print("You must enter Y or N!")
				continue

			return_dict = {
				'url_txt_file_path': url_txt_file_path,
				'folder_file_path': folder_file_path,
				'org_name': org_name,
				'fb_username': fb_username,
				'chrome_profile_path': chrome_profile_path,
				'chrome_profile_name': chrome_profile_name,
				'DEBUG_MODE': debug_mode.lower(),
				'start_line_num': start_line_num,
				'end_line_num': end_line_num,
			}		

		except ValueError as e:
			print("Invalid input! Try again!\n")
			continue

		return return_dict 

def update_archive_file(id_of_vid, status, archive_file_path, error_msg = None):
	if os.path.isfile(archive_file_path): # Check if the archive file exists
		while True:
			try:
				archive_file_df = pd.read_csv(archive_file_path, index_col=None)
			except Exception as e:
				logger.warning('Error accessing CSV file... retrying in 3 secs')
				sleep(3)
				continue

			if int(id_of_vid) in archive_file_df['id'].values:
				archive_file_df.loc[archive_file_df['id'] == int(id_of_vid), ['status']] = status
				if status == 'error':
					archive_file_df.loc[archive_file_df['id'] == int(id_of_vid), ['error_msg']] = error_msg
				elif status == 'done':
					archive_file_df.loc[archive_file_df['id'] == int(id_of_vid), ['error_msg']] = ''
				break
				
			else:
				archive_file_df = archive_file_df.append({
					'id': id_of_vid,
					'status': status,
					'error_msg': error_msg,
					}, ignore_index=True)
				break


	else:
		archive_file_df = pd.DataFrame(columns=['id','status', 'error_msg'])
		archive_file_df = archive_file_df.append({
			'id': id_of_vid,
			'status': status,
			'error_msg': error_msg,
			}, ignore_index=True)

	archive_file_df.to_csv(archive_file_path,index=False)

def find_fb_video_download_url(html_content):
	
	while True:

		# Check if temporarily blocked
		temporarily_blocked_regex = re.compile("temporarily blocked")
		temporarily_blocked_results = re.search(temporarily_blocked_regex, html_content.lower())
		
		# if temporarily blocked: 
		if temporarily_blocked_results != None:
			mins_to_wait = randint(90,180)
			logger.error(f'Temporarily blocked. Waiting for {mins_to_wait} min before retry...\nNote: usually, you must wait for at least 90 mins or longer before FB will unblock you.')
			sleep(mins_to_wait*60)
			return {
				'status': 'fail_temp_blocked',
			}
			continue

		# Check if video has been removed
		content_not_available_regex = re.compile("this content isn't available")
		content_not_available_results = re.search(content_not_available_regex, html_content.lower())
		if content_not_available_results != None:
			logger.error('Content not available!')
			update_archive_file(id_of_vid, 'error', archive_file_path, 'content_not_available')

			# Wait 10-40 secs before downloading next link, to avoid being banned by FB (FB has strict rate limits).
			wait_interval = randint(10,40)
			logger.info("Waiting " + str(wait_interval) + " secs...")
			sleep(wait_interval)

			return {
				'status': 'fail'
			}
			break

		# ======================================
		# FIND FB VIDEO LINK:
		# See here for detailed explanation on below code: https://www.reddit.com/r/software/comments/9h5kz3/software_or_website_to_download_facebook_videos/	

		video_tag_exists = False
		vid_urls = ''

		# Find if <video> tag exists
		soup = BeautifulSoup(html_content, 'html.parser')#lxml')#html.parser')

		video_tag = soup.find_all('video')
		if video_tag != []:
			#logger.debug('found video tag')

			for tag in video_tag:
				#logger.debug(tag)
				if 'blob' not in tag.get('src'):
					#logger.debug('no blob')
					vid_urls =  tag.get('src')
					#logger.debug(vid_urls)
					video_tag_exists = True
					break
		# else:
		# 	logger.debug('no video tags found')

		if video_tag_exists == False:
 			# Find URLs inside resolutions (tag on FB video URL page source: <FBQualityLabel>) and quality classes (tag on FB video URL page source: <FBQualityClass>)
 			resolutions = ['1080p','720p','480p','360p','240p','Source','source',]
			quality_class_list = ['hd', 'sd']

			vid_regex = {}
			vid_regex_results = {}

			for resolution in resolutions:
				vid_regex[resolution] = re.compile(resolution + '(.*?)">(.*?)u003CBaseURL>https:(.*?)BaseURL')
				vid_regex_results[resolution] = re.search(vid_regex[resolution], html_content)


		# # Find the video link in the returned HTML content.
		# # Try 1080P first, if no 1080P, then try finding 720P, 480P, 360P links.
		# vid_regex = re.compile('1080p(.*?)">(.*?)u003CBaseURL>https:(.*?)BaseURL')
		# vid_regex_results = re.search(vid_regex, html_content)

		# # If no 1080p link
		# if vid_regex_results != None:
		# 	# Try finding 720p link
		# 	vid_regex = re.compile('720p(.*?)">(.*?)u003CBaseURL>https:(.*?)BaseURL')
		# 	vid_regex_results = re.search(vid_regex, html_content)

		# 	if vid_regex_results != None:
		# 		logger.debug('720p')
		# 	else:
		# 		# Try 480p
		# 		vid_regex = re.compile('480p(.*?)">(.*?)u003CBaseURL>https:(.*?)BaseURL')
		# 		vid_regex_results = re.search(vid_regex, html_content)
				
		# 		if vid_regex_results != None:
		# 			logger.debug('480p')
		# 		else:
		# 			# Try 360p
		# 			vid_regex = re.compile('360p(.*?)">(.*?)u003CBaseURL>https:(.*?)BaseURL')
		# 			vid_regex_results = re.search(vid_regex, html_content)

		# 			if vid_regex_results != None:
		# 				logger.debug('360p')
		# 			else:
		# 				# Try 240p
		# 				vid_regex = re.compile('240p(.*?)">(.*?)u003CBaseURL>https:(.*?)BaseURL')
		# 				vid_regex_results = re.search(vid_regex, html_content)

		# 				if vid_regex_results != None:
		# 					logger.debug('240p')
		# 				else:
		# 					# Find if video tag exists
		# 					soup = BeautifulSoup(html_content, 'html.parser')#lxml')#html.parser')
		# 					video_tag = soup.find('video')
		# 					if video_tag != None:
		# 						video_tag_exists = True
		# 						logger.debug('found video tag')
		# 						vid_urls =  video_tag.get('src')
		# 					else:
		# 						logger.debug('nothing found')
						

		# Process the URL, get rid of extra characters

		# if <video> tag exists, we can just use its 'src' attribute, no need to get rid of extra characters
		if video_tag_exists == False: 
			non_hvideo_video = False

			# Test highest resolutions first (1080p, then 720p, etc)
			for resolution in resolutions:
				try:
					vid_urls = vid_regex_results[resolution].group()
					vid_regex_2 = re.compile('https:(.*?)u003C')
					vid_regex_results_2 = re.search(vid_regex_2, vid_urls)
					vid_urls = vid_regex_results_2.group()
					logger.debug(vid_urls)
					vid_urls = vid_urls[0:-6]
					vid_urls = vid_urls.replace('\/','/')
					vid_urls = vid_urls.replace('&amp;','&')

					# Video URLs with "hvideo" in them can't be downloaded, so skip.
					if 'hvideo' not in vid_urls:
						logger.debug(f'Found link: {resolution}')
						non_hvideo_video = True
						break

				except AttributeError as e:
					# This means a video doesn't exist for this resolution, so try other resolutions.
					if str(e) == "'NoneType' object has no attribute 'group'":
						continue
					else:
						logger.error(e)
						return {
							'status': 'fail',
						}
			
			# If can't find a working video URL in resolution, try quality_class 
			if non_hvideo_video == False:

				for quality_class in quality_class_list:
					vid_regex[quality_class] = re.compile(quality_class + '(.*?)">(.*?)u003CBaseURL>https:(.*?)BaseURL')
					vid_regex_results[quality_class] = re.search(vid_regex[quality_class], html_content)


				for quality_class in quality_class_list:
					try:
						vid_urls = vid_regex_results[resolution].group()
						vid_regex_2 = re.compile('https:(.*?)u003C')
						vid_regex_results_2 = re.search(vid_regex_2, vid_urls)
						vid_urls = vid_regex_results_2.group()
						logger.debug(vid_urls)
						vid_urls = vid_urls[0:-6]
						vid_urls = vid_urls.replace('\/','/')
						vid_urls = vid_urls.replace('&amp;','&')

						if 'hvideo' not in vid_urls:
							logger.debug(f'Found link: {resolution}')
							non_hvideo_video = True
							break
					except AttributeError as e:
    					# This means a video doesn't exist for this quality_class, so try other quality_class.
						if str(e) == "'NoneType' object has no attribute 'group'":
							continue
						else:
							logger.error(e)
							return {
								'status': 'fail',
							}

		logger.debug(f'Video link: {vid_urls}\n')

		# FIND FB AUDIO LINK:
		if video_tag_exists == False: # if <video> tag exists, no need to find a separate audio link
			audio_regex = re.compile('audio_channel(.*?)BaseURL>https:(.*?)BaseURL>')
			audio_regex_results = re.search(audio_regex, html_content)
			audio_urls = audio_regex_results.group()

			# Process the audio URL, get rid of extra characters
			audio_regex_2 = re.compile('https:(.*?)u003C')
			audio_regex_results_2 = re.search(audio_regex_2, audio_urls)
			audio_urls = audio_regex_results_2.group()
			audio_urls = audio_urls[0:-6]
			audio_urls = audio_urls.replace('\/','/')
			audio_urls = audio_urls.replace('&amp;','&')

			logger.debug(f'Audio link: {audio_urls}\n')
		else:
			audio_urls = None

		status = 'ok'

		return {
			'status': status,
			"vid_urls": vid_urls,
			'audio_urls': audio_urls,
			'video_tag_exists': video_tag_exists,
		}



# =============================================
if __name__ == '__main__':

	# Initialize argument parser
	parser = argparse.ArgumentParser()
	parser.add_argument("-u", "--url_txt", dest="url_txt_file_path",
	                    help="Path to .txt file containing FB Video URLs", metavar="URL_TXT_FILE_PATH")

	# Optional
	parser.add_argument("--start", dest="start_line",
	                    action="store", default=None, help="Start reading URL .txt file from line", metavar="START_LINE_NUMBER")

	# Optional
	parser.add_argument("--end", dest="end_line",
	                    action="store", default=None, help="End reading URL .txt file at line", metavar="END_LINE_NUMBER")

	parser.add_argument("-fo", "--folder", dest="folder_file_path",
	                    help="Path to folder to save videos in", metavar="FOLDER_PATH")

	parser.add_argument("-o", "--org_name", dest="org_name",
	                    help="Name of media organization, used for file naming", metavar="MEDIA_ORG")

	parser.add_argument("-fb", "--fb_user", dest="fb_username",
	                    help="Username of FB profile you are downloading", metavar="FB_USERNAME")

	# Optional
	parser.add_argument("-cp", "--chrome_path", dest="chrome_profile_path",
	                    help="Path to Chrome profile folder",  metavar='CHROME_PROFILE_PATH')

	# Optional
	parser.add_argument("-cn", "--chrome_name", dest="chrome_profile_name",
	                    help="Name of Chrome profile",  metavar='CHROME_PROFILE_NAME')

	# Optional
	parser.add_argument("-d", "--debug", dest="DEBUG_MODE",
	                    action="store_true", default=False, help="Print debug messages")

	args = parser.parse_args()
	
	# Parse arguments
	if len(sys.argv) > 1:
		try:
			url_txt_file_path = args.url_txt_file_path
			folder_file_path = args.folder_file_path
			org_name = args.org_name
			fb_username = args.fb_username
			chrome_profile_path = args.chrome_profile_path
			chrome_profile_name = args.chrome_profile_name
			DEBUG_MODE = args.DEBUG_MODE
		except Exception as e:
			print("ERROR with arguments. Try again.")
			print(e)
		try: 
			start_line_num = int(args.start_line)
			end_line_num = int(args.end_line)
		except Exception as e:
			pass

	# Get arguments through CLI
	if len(sys.argv) == 1:
		args = get_input_variables()

		url_txt_file_path = args['url_txt_file_path']
		folder_file_path = args['folder_file_path']
		org_name = args['org_name']
		fb_username = args['fb_username']
		chrome_profile_path = args['chrome_profile_path']
		chrome_profile_name = args['chrome_profile_name']
		DEBUG_MODE = args['DEBUG_MODE']
		start_line_num = args['start_line_num']
		end_line_num = args['end_line_num']


	# Check if last char of folder_file_path is '\' or '/', if not, add '\' or '/'
	if sys.platform == 'win32' and folder_file_path[-1] != '\\':
		folder_file_path += '\\'
	elif folder_file_path[-1] != '/':
		folder_file_path += '/'

	if folder_file_path == '':
		folder_file_path = os.getcwd()

	if chrome_profile_path == '':
		if sys.platform == 'linux' or sys.platform == 'linux2':
			chrome_profile_path = f'/home/{os.getlogin()}/.config/google-chrome/'
		elif sys.platform == 'darwin':
			chrome_profile_path = f'Users/{os.getlogin()}/Library/Application Support/Google/Chrome/'
		elif sys.platform == 'win32':
			chrome_profile_path = f'C:\\Users\\{os.getlogin()}\\AppData\\Local\\Google\\Chrome\\User Data\\'

	# The archive file records if you have downloaded a particular video already
	# Ex: C:\users\yourusername\Desktop\hkcnews\hkcnews_archive.txt 
	archive_file_path = folder_file_path + org_name + '_archive.csv'

	# =======================================================
	# Set up logger
	logger = logging.getLogger(__name__)
	formatter = logging.Formatter('%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s')

	if DEBUG_MODE == True:
		logger.setLevel(logging.DEBUG)
	else:
		logger.setLevel(logging.INFO)
	
	# used for file naming
	now_as_string = datetime.now().strftime('%Y%m%d_%H%M')

	# Create a log file to store output of program
	if not os.path.exists(f'{folder_file_path}/logs'):
		os.makedirs(f'{folder_file_path}/logs')
	file_handler = logging.FileHandler(f'{folder_file_path}/logs/{org_name}_{now_as_string}_log.txt')
	logger.addHandler(file_handler)
	file_handler.setFormatter(formatter)


	# Show logs on screen
	stream_handler = logging.StreamHandler()
	logger.addHandler(stream_handler)
	stream_handler.setFormatter(formatter)



	# ====================================================
	# Main code

	# Read list of URLs to download
	with open(url_txt_file_path) as f:
		total_number_of_urls_in_file = len(f.readlines())
		f.close()

	with open(url_txt_file_path) as f:
		if 'start_line_num' in locals():
			if start_line_num is not None:
				number_of_lines_to_read = end_line_num - start_line_num

				urls = []
				for i in range(start_line_num):
					next(f)
				
				line_counter = 0

				for line in f:
					line_counter += 1
					if line_counter <= number_of_lines_to_read:
						urls.append(line)

				logger.info(f'Reading URL {start_line_num} to {end_line_num} ({number_of_lines_to_read + 1} lines)')
		else:			
			urls = f.readlines()

	logger.info(f'URLs in {url_txt_file_path}: {len(urls)}')

	# For debugging:
	#urls = ['https://www.facebook.com/watch/?v=319284099859384'] 

	# Download URLs
	counter = 0

	is_driver_running = False

	for url in urls:
		counter += 1
		logger.debug("***************************************************")

		if 'start_line_num' in locals():
			logger.info(f"Downloading video #{str(counter)}/{len(urls)} (video # {str(start_line_num + counter - 1)}/{total_number_of_urls_in_file}):")
		else:
			logger.info(f"Downloading video #{str(counter)}/{len(urls)}:")

		
		while True:
			try:
				id_of_vid = url.replace('https://www.facebook.com/' + fb_username + '/videos/', '')
				# Get the ID of the video (usually 15-17 digits, ex: 319284099859384)
				id_of_vid = id_of_vid.replace('/', '')
				id_of_vid = id_of_vid.replace('\n', '')
				url = url.replace('\n','')
				logger.info(f'Video ID: {id_of_vid}')

				# Check if this video has been downloaded already, if so, skip.
				# If a file is downloaded, the archive file will have a line saying "<id of vid>,done"
				# Ex: "319284099859384,done"
				if os.path.isfile(archive_file_path): # Check if the archive file exists
					while True:
						try:
							archive_file_df = pd.read_csv(archive_file_path, index_col=None)
							break
						except pd.errors.EmptyDataError as e:
							logger.warning('CSV file in use. Waiting 3 secs before trying to read again...')
							sleep(3)
							continue

					# See if there are any non-integers in id column
					while True:
						try:
							archive_file_df['id'].values.astype('int')
							break
						except ValueError as e:
							archive_file_df = archive_file_df[pd.to_numeric(archive_file_df['id'], errors='coerce').notnull()]
							logger.warning('Warning! Archive CSV file, in "id" column! \
								This column should only have integers, but it has non-integers. Will try to rewrite CSV file to delete non-integer rows.')
							archive_file_df.to_csv(archive_file_path,index=False)
							#traceback.print_exc()
							#sys.exit()

					if int(id_of_vid) in archive_file_df['id'].values:
						#print('found id')
						status = archive_file_df.loc[archive_file_df['id'] == int(id_of_vid),'status'].tolist()[-1]
						error_msg = archive_file_df.loc[archive_file_df['id'] == int(id_of_vid),'error_msg'].tolist()[-1]

						if status == 'done':
							logger.info(f"Already downloaded: {id_of_vid}")
							break		
						elif status == 'error' and error_msg == 'content_not_available':
							logger.info(f"Content not available [based on previous run]: {id_of_vid}")
							break

				# ======================================
				# If Video has not been downloaded before, then:
				# Make a HTTP GET request to fetch the raw HTML content of the video link.

				options = webdriver.ChromeOptions()

				# Use your Chrome profile, where you already logged into FB.
				# Chrome profiles: read https://stackoverflow.com/questions/52394408/how-to-use-chrome-profile-in-selenium-webdriver-python-3/67389309#67389309
				#print(f'chrome profile path: {chrome_profile_path}')
				#print(f'chrome profile name: {chrome_profile_name}')
				user_data_dir_argument = f'--user-data-dir={chrome_profile_path}'
				options.add_argument(user_data_dir_argument)
				# Most profiles are called "Default", if you have error when opening Chrome, then try changing to your profile name. 
				profile_directory_argument = f'--profile-directory={chrome_profile_name}' # Ex: --profile-directory=Profile 3
				options.add_argument(profile_directory_argument)

				# If this Chrome is not working, try uncommenting this line.
				# options.add_argument("--disable-dev-shm-usage")

				# Start webdriver
				if is_driver_running == False:
					driver = webdriver.Chrome(options=options)
					is_driver_running = True
				#url='ip-adress.com' For debugging
				logger.debug(f'Video page URL: {url}')

				while True:
					driver.get(url)
					is_driver_running = True

					# Get the returned HTML content
					html_content = driver.page_source

					# For debugging
					# with open('html_content.txt','w') as f:
					# 	f.write(html_content)
					# 	f.close()
					
					fb_video_url_return_dict = find_fb_video_download_url(html_content)

					if fb_video_url_return_dict['status'] == 'fail_temp_blocked':
						driver.quit()
						is_driver_running = False
						continue
					elif fb_video_url_return_dict['status'] == 'fail':
						logger.error(f'Cannot find video URL for {id_of_vid}')
						break
					else:
						break


				vid_urls = fb_video_url_return_dict['vid_urls']
				audio_urls = fb_video_url_return_dict['audio_urls']
				video_tag_exists = fb_video_url_return_dict['video_tag_exists']


				# ======================================
				# DOWNLOAD VIDEO and display progress bar. 
				# As noted above, we download the FB video and audio files separately, you must 
				# then use FFMpeg to combine them, see beginning of this file for instructions.

				bar = ProgressBar(template="Download |{animation}| {done:B}/{total:B} {percent} {elapsed} {tta} ")
				logger.debug(f'Downloading video... {vid_urls}\n')
				urllib.request.urlretrieve(vid_urls, folder_file_path + id_of_vid + "_video.mp4", bar.on_urlretrieve)
				
				# DOWNLOAD AUDIO and display progress bar
				if video_tag_exists == False:
					logger.debug(f'Downloading audio... {audio_urls}\n')
					urllib.request.urlretrieve(audio_urls, folder_file_path + id_of_vid + "_audio.mp4", bar.on_urlretrieve)

				# Update archive, to say this link has been downloaded.
				logger.info('Updating archive...')
				update_archive_file(id_of_vid, 'done', archive_file_path)

				# Wait for 10-40 secs
				wait_interval = randint(10,40)
				logger.info("Waiting " + str(wait_interval) + " secs...")
				sleep(wait_interval)

				if counter == len(urls):
					driver.close()
					is_driver_running = False

				break


			except Exception as e:
				# Print error
				logger.error(e)
				logger.error("Error: " + url)

				if str(e) == 'HTTP Error 418: Bad request - Invalid URL':
					update_archive_file(id_of_vid, 'error', archive_file_path, '418_invalid_url')
				else:
					# Update archive, to say this link had an error.      
					error_msg = str(e)
					error_msg = error_msg.replace('\n','')

					update_archive_file(id_of_vid, 'error', archive_file_path, error_msg)

				# Wait for 10-40 secs
				wait_interval = randint(10,40)
				logger.info("Waiting " + str(wait_interval) + " secs...")
				sleep(wait_interval)

				driver.quit()
				is_driver_running = False

				break
