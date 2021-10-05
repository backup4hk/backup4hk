# Shared functions for IG scripts
import requests, time, logging, json, sys
from random import randint

logger = logging.getLogger(__name__)

# Read a TXT file
def read_txt_file(txt_file_path):
	with open(txt_file_path, 'r') as f:
		lines = f.readlines()
	return lines

# Returns a JSON object
# type_of_call: can be "end_cursor"
def call_ig_api(url_api, headers, type_of_call, proxies=None):
	num_of_429_errors = 0

	logger.info("Pulling from IG API...")

	while True:
		if proxies != {} and proxies != None:
			test_proxy_request = requests.get('https://www.ifconfig.me', proxies=proxies)
			logger.debug(f"Proxy test: Your IP address is seen as: {test_proxy_request.text}")
			time.sleep(3)
			r = requests.get(url_api, headers=headers, proxies=proxies)
		else:
			logger.debug("No proxy used")
			r = requests.get(url_api, headers=headers)

		#logger.debug(r.status_code)
		#logger.debug(r.text)

		# Try to load JSON object from r.text
		try:
			json_return = json.loads(r.text)
		except Exception as e:
			logger.critical(f"Error with Returned JSON")
			if r.text.find('<html lang="en" class="no-js not-logged-in client-root">') != -1:
				logger.critical('IG login page returned. Login to IG on a browser with this IP address, then retry this script.')
				sys.exit()
			else:
				logger.debug(e)
				logger.debug("Returned JSON:")
				logger.debug(r.text)

			return None

		if type_of_call == 'main_page_of_profile':
			logger.debug('')
			#logger.debug('main_page_of_profile call')
		
		elif type_of_call == 'end_cursor':
			#logger.debug('end_cursor call')

			# Check if JSON returned status of "ok"
			status = json_return['status']
			#logger.debug(f'Status: {status}')

			# If status was NOT ok.
			if status != 'ok':
				logger.error(f"Request returned a failure")

				# If 429 HTTP error returned, timeout BEFORE retrying the API call
				if str(r.status_code) == '429':
					num_of_429_errors += 1

					random_minutes_lower_bound = 9 + (20 * (num_of_429_errors - 1))
					random_minutes_upper_bound = 19 + (20 * (num_of_429_errors - 1))

					random_minutes = randint(random_minutes_lower_bound,random_minutes_upper_bound)
					logger.error(f'HTTP 429 code returned: Too many requests. Waiting for {random_minutes} mins before next API call.\nIG API will temporary block you if you call their API too many times in short period of time. So we must wait before calling API again. \nPlease WAIT. Script will automatically continue in {random_minutes} mins.')
					time.sleep(random_minutes * 60)

				#logger.debug(r.text)
				logger.info(f"Retrying this API call...")
				continue

		break
	return json_return

def timeout(parameters_dict):
	secs_to_wait_min = parameters_dict['secs_to_wait_min']
	secs_to_wait_max = parameters_dict['secs_to_wait_max']
	number_of_pulls_before_long_pull = parameters_dict['number_of_pulls_before_long_pull']
	mins_to_long_wait_min = parameters_dict['mins_to_long_wait_min']
	mins_to_long_wait_max = parameters_dict['mins_to_long_wait_max'] 

	if randint(1,number_of_pulls_before_long_pull) == 1:
		mins_to_wait_long_wait = randint(mins_to_long_wait_min, mins_to_long_wait_max)

		logger.info(f'LONG waiting {mins_to_wait_long_wait} mins before pull next page...')
		logger.info(f'This is NOT an error. Please relax and WAIT for {mins_to_wait_long_wait} mins. This prevents being blocked by IG. This is set to happen roughly every ~{number_of_pulls_before_long_pull} pulls (may be higher or lower).')
		logger.info(f'Change "number_of_pulls_before_long_pull", "mins_to_long_wait_min", and "mins_to_long_wait_max" variables to adjust the frequency of this.')

		time.sleep(mins_to_wait_long_wait*60)

	seconds_to_wait = randint(secs_to_wait_min,secs_to_wait_max)
	logger.info(f'Waiting {seconds_to_wait} secs before pulling...')
	time.sleep(seconds_to_wait)

	return
