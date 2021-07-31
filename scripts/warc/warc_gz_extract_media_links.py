"""
WARC GZ file 尋找所有媒體媒體連結 python script
Get all media links from a WARC.GZ file
Media links include audio (.mp3, etc) and video (.mp4, etc)

注意: 複雜d嘅英文先會翻譯到中文

REQUIREMENTS:
1. Install warcio. https://pypi.org/project/warcio/

TO USE 使用步驟:
1. Find the path to folder with .warc.gz files (ex: C:/users/hk/Desktop/backup)

2. Open a .warc.gz file, then extract the .warc file。 
用任何一個開到 .gz 壓縮檔案既program 打開個 .warc.gz file （Google大把，例如 7 zip, winzip; winrar 唔 support），
裡面有一個 .warc file，extract佢出黎

3. Open the .warc file with an IDE like Sublime Text. 
用你常用IDE例如visual studio code, Sublime Text 或甚至原始d notepad打開 .warc file.

4. Do CTRL+F for .mp3, .mp4, etc. Look at the links for .mp3 / .mp4。 
係 warc 檔案裏面用 CTRL-F 尋找 .mp3, .mp4 等唔同 file extension，
應該會找到好多條link 例如 https://podcast.rthk.hk/podcast/media/rthkmemory/c_a26.mp3, 
可以試copy paste條link去遊覽器係會work既。

5. Write a "regular expression" to extract .mp3/.mp4. Use regex101.com and Youtube and Google for help. 
寫個regular expression黎一次過extract哂所有link。建議你將 Warc file 裡面幾個.mp3 .mp4等連結抄到 regex101.com，
然後試幾個 regular expression 直至到有個regular expression係成功extract到所有條 .mp3, .mp4 link. 
如果唔識 regex，上 YouTube 睇 tutorial, 你有最基本寫電腦程式既 experience 睇10分鐘就會明。

簡單regular expression 例子 (你regular exprsession 有可能會複雜一些先得):
例子 1， extract mp3 link： http.*?.mp3
例子 2, extract mp4 link: http.*?.mp4

6. Paste regular expression below, in code, where it says "PASTE REGULAR EXPRESSION HERE". 

7. Run: 
python3 warc_gz_extract_media_links.py <path to folder with .warc.gz files> <organization name>
(organization name is used for filename. Example: "rthk", "standnews")

"""

import sys, re, glob, os, urllib.parse, time
from warcio.archiveiterator import ArchiveIterator

# ===================================
# Helper Function

# Remove duplicates from a list
def remove_duplicates(orig_list): 
	new_list = []
	for item in orig_list:
		if item not in new_list:
			new_list.append(item)

	return new_list

# ===================================
# Main functions

# Get list of .warc.gz files from folder
file_list = []
os.chdir(sys.argv[1])
for file in glob.glob("*.warc.gz"):
	file_list.append(file)

# List of file extension (ex: .mp3) to find links for, can add/edit if needed
audio_file_exts = ['.3ga','.aac','.aif','.aifc','.aiff','.dts','.dtshd','.fl','.flac','.flp','.g726','.gsm',
		   '.m3u','.m3u8','.m4a','.m4b','.midi','.mp2','.mp3','.odm','.oga','.ogg','.pcast','.raw','.wav','.wma',]
video_file_exts = ['.webm','.flv','.mpg', '.mp2', '.mpeg', '.mpe', '.mpv','.ogg','.mp4', '.m4p', '.m4v',
		   '.avi', '.mkv','.wmv','.mov', '.qt','.flv', '.swf','.avchd','.webp','.ts',]
all_file_exts = audio_file_exts + video_file_exts

if len(sys.argv) != 3:
	print("You must enter 2 arguments!\nArgument 1: path to folder with warc.gz files. \
	Example: C:/users/yourname/Desktop/backup\n\
	Argument 2: organization name, used for file naming. Example: rthk\n")
	sys.exit()


file_counter = 0
media_uri = []
org_name = sys.argv[2]

# Loop through every .warc.gz file in folder
for file in file_list:
	file_counter += 1

	print(f'Processing #{file_counter}/{len(file_list)}: {file}') 
	time.sleep(2)

	with open(file, 'rb') as stream:
		for record in ArchiveIterator(stream):

			# Find links to .mp3, .mp4 etc files
			for ext in all_file_exts:                
				'''
				PASTE REGULAR EXPRESSION BELOW, as argument to re.compile
				If regex has "\", add another "\", so it is "\\".
				ext_regex = re.compile(<regex> + ext)
				'''
				ext_regex = re.compile('https%3A.*\\' + ext)

				# WARC-Target-URI
				result_list = [x.group() for x in re.finditer(ext_regex, \
									      str(record.rec_headers.get_header('WARC-Target-URI')))]
				for item in result_list:
					media_uri.append(item)

				# HTTP_headers
				result_list = [x.group() for x in re.finditer(ext_regex, str(record.http_headers))]
				for item in result_list:
					media_uri.append(item)                

		print(f'Found {len(media_uri)} URIs in this file')

# Deduplicate media_uri list
print(f'Deduplicating {len(media_uri)} URIs...')
media_uri = remove_duplicates(media_uri)
print(f'Unique URIs left: {len(media_uri)}')

# Decode URI links
for i in range(0,len(media_uri)):
	media_uri[i] = urllib.parse.unquote(media_uri[i])

# Print media uris, and save them
#print(media_uri)
with open(sys.argv[1] + org_name + '_warc_media_uris.txt', 'w') as f:
	for uri in media_uri:
		f.write(uri + "\n")
f.close()
