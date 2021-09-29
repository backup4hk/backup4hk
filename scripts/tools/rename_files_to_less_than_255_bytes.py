'''
Rename files so file names are less than 255 bytes
Last updated: 2021-09-29

Arguments:
Arg #1. path to folder, with files that you want to rename (ex: C:/users/hk/Desktop/rthk)
Arg #2. If you want to do a dry run to see what files will be renamed, 
type --dry-run (this is optional)
A dry run will return a .csv file with list of files that will be renamed. No files will actually be renamed.

Example: rename_files_less_than_255_bytes.py C:/users/hk/Desktop/rthk

'''
import csv, sys, os, re, logging
from datetime import datetime
from pathlib import Path
from string import punctuation

global now_as_string
now_as_string = datetime.now().strftime('%Y%m%d_%H%M')

# Create list of punctuation marks 
# We will delete punctuation marks from the filenames, except for periods "."
punctuation_without_period = punctuation.replace('.','')
punctuation_without_period += "！？｡。＂＃＄％＆＇（）＊＋，－／：；＜＝＞＠［＼］＾＿｀｛｜｝～｟｠｢｣､、〃》「」『』【】〔〕〖〗〘〙〚〛〜〝〞〟〰〾〿–—‘’‛“”„‟…‧﹏# "

# Set up logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s')
stream_handler = logging.StreamHandler()
logger.addHandler(stream_handler)
stream_handler.setFormatter(formatter)


# Helper functions
# ========================================

# Rename a filename to less than 255 bytes
# Inputs: 
# 1. filename_without_ext: filenmae without extension 
# 2. ext: file extension
# Example: if a file name is "myphoto001.jpeg", filename_without_ext is myphoto001, ext is .jpeg
def rename_filename_to_less_than_255(filename_without_ext, ext):

    # logger.debug('entered filename_without_ext: ' + filename_without_ext)
    # logger.debug('ext: ' + ext)
    # logger.debug(utf8len(filename_without_ext + ext))

    # If filename less than 255 bytes, return filename.
    if utf8len(filename_without_ext + ext) <= 255:
        return filename_without_ext + ext

    # note that for files with multiple periods in filename, ext will include all strings past the first period
    # ex: "20201103 - 11.2海外網友.mp4": ext will contain '2海外網友.mp4'.
    # for this reason, we want to leave some filename_without_ext characters (i.e. not delete them all). Here, this is set to 20 characters.
    if len(filename_without_ext) <= 20:
        if utf8len(filename_without_ext + ext) <= 255:
            return filename_without_ext + ext
        else:
            # Check if last character in ext is chinese or a punctuation mark (excluding period). If yes, delete from ext.
            # (chinese chars and non-period punctuation marks cannot be file exts, so we can delete this char from ext)
            # (exclude important chinese characters 年, 月, 日, etc from being deleted, we want to keep those)
            for i in range(len(ext) - 1, 1, -1):
                if ext[i] in punctuation_without_period or \
                (re.search(u'[\u4e00-\u9fff]',ext[i])
                and (not re.search(u'[\u5e74]',ext[i]) and not re.search(u'[\u6708]',ext[i]) and not re.search(u'[\u65e5]',ext[i]) and not re.search(u'[\u96c6]',ext[i]))): # it is a chinese character that is NOT 年,月,日,集
                    return rename_filename_to_less_than_255(filename_without_ext, ext[0:i] + ext[i+1:])
            else:
                return False

    # Delete the rightmost character, then check if utf8len <= 255 thru recursion.
    return rename_filename_to_less_than_255(filename_without_ext[0:-1], ext)

# Return number of bytes of string "s"
def utf8len(s):
    return len(s.encode('utf-8'))

def rename_files(folder_path, DRY_RUN_MODE=True):
    num_files_renamed = 0
    renamed_log = {}

    # Generator that traverses through all folders and subfolders
    # from: https://stackoverflow.com/a/10989155/
    for path, subdirs, files in os.walk(folder_path):
        # For every file:
        for old_name in files:

            # if old name length > 255 bytes:
            if utf8len(old_name) > 255:
                num_files_renamed += 1

                # logger.debug('\n***********************************************')
                
                # Get file extensions, starting from the first period in filename
                # Ex: if a file is 'a.txt', ext will be '.txt'
                # Ex: if a file is '1.2.3.4.jpg', ext will be '.2.3.4.jpg'
                ext = ''.join(Path(old_name).suffixes)
                # Use regex to get old name of file (without extension, where extension is everything starting from the first period in filename)
                # Ex: if a file is 'a.txt', old name of file without extension is 'a'
                # Ex: if a file is '1.2.3.4.jpg', old name of file without extension will be '1'
                old_name_without_ext = re.sub(re.compile(re.escape(ext) + '$'),'', old_name)

                new_name = rename_filename_to_less_than_255(old_name_without_ext, ext)                
                renamed_log[old_name] = [new_name, path]

                # Check if rename_filename_to_less_than_255 returned a new file name.
                if new_name != False:
                    logger.debug(f'Renaming file #{num_files_renamed}: \nFROM: "{old_name}" \nTO: "{new_name}"')
                    file_path = os.path.join(path,old_name)
                    new_name = os.path.join(path,new_name)
                    if DRY_RUN_MODE == False:
                        os.rename(file_path, new_name)
                    else:
                        logger.info('This is a dry run! No files will actually be renamed!')
                else:
                    logger.error(f'Could not rename {old_name}, could not find shorter filename less than 255 bytes')


    if not os.path.exists('log/rename_files_to_less_than_255_bytes'):
        os.makedirs('log/rename_files_to_less_than_255_bytes')

    directory_without_punctuation = re.sub(r'[^\w\s]', '_', directory, re.UNICODE)
    if DRY_RUN_MODE == False:
        csv_file_path = 'log/rename_files_to_less_than_255_bytes/rename_files_' + directory_without_punctuation + '_' + now_as_string + '_log.csv'
    else:
        csv_file_path = 'log/rename_files_to_less_than_255_bytes/rename_files_' + directory_without_punctuation + '_' + now_as_string + '_DRYRUN_log.csv'

    with open(csv_file_path, 'w', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter='\t')
        writer.writerow(['old_name','new_name','directory'])

        for key, value in renamed_log.items():
            if value != None:
                writer.writerow([key, value[0], value[1]])
            else:
                writer.writerow([key, 'ERROR_COULD_NOT_CREATE_SHORTER_FILENAME_LESS_THAN_255_BYTES',''])

        f.close()

    if DRY_RUN_MODE == False:
        logger.info(f'CSV file of filename changes created at: {csv_file_path}!')
    else:
        logger.info(f'DRY RUN CSV file of filename changes created at: {csv_file_path}!')

    return {
        'files_renamed': num_files_renamed,
        'renamed_log': renamed_log
    }

# Run script
# ========================
if __name__ == '__main__':
    # Get arguments
    if len(sys.argv) == 1:
        logger.critical('No arguments entered! Exiting!')
        sys.exit()
    directory = sys.argv[1] # Argument #1
    DRY_RUN_MODE = False
    if len(sys.argv) == 3:
        if sys.argv[2] == '--dry-run':
            DRY_RUN_MODE = True
    elif len(sys.argv) > 3:
        logger.critical('Too many arguments entered! Exiting!')
        sys.exit()

    logger.info(f'Renaming all files in: {directory}')

    if DRY_RUN_MODE == False:
        confirmation = input(f'Are you sure you want to RENAME files in {directory}? THIS CANNOT BE UNDONE. Type YES to continue.\n')
        if confirmation.lower() == 'yes':
            rename_result = rename_files(directory, DRY_RUN_MODE)
            logger.info('Files renamed: ' + str(rename_result['files_renamed']))
        else:
            logger.warning('YES not entered. Exiting!')
    else:
        rename_result = rename_files(directory, DRY_RUN_MODE)
        logger.info('DRY RUN: This would have renamed: ' + str(rename_result['files_renamed']) + ' files. No files were actually renamed as this is a dry run.')

