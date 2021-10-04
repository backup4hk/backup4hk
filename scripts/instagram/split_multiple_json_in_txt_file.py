from json import JSONDecoder
from functools import partial
import pandas as pd, logging
logger = logging.getLogger(__name__)

# =================================
# Read in a .txt/.json file with many JSON objects, one after the other 
# (i.e. this .txt and .json file are not valid)
# Reference: https://stackoverflow.com/questions/21708192/how-do-i-use-the-json-module-to-read-in-one-json-object-at-a-time

# Helper function
def json_parse(fileobj, decoder=JSONDecoder(), buffersize=2048):
    buffer = ''
    for chunk in iter(partial(fileobj.read, buffersize), ''):
         buffer += chunk
         while buffer:
             try:
                 result, index = decoder.raw_decode(buffer)
                 yield result
                 buffer = buffer[index:].lstrip()
             except ValueError:
                 # Not enough data to decode, read more
                 break

# =================================
# Main function

def split_multiple_ig_jsons(path_to_input_json_file):
    counter = 0

    df = pd.DataFrame()

    with open(path_to_input_json_file, 'r') as infh:

        for data in json_parse(infh):
            counter += 1
            logger.info(f'Merging JSON #{counter}...')
            df = df.append(data, ignore_index=True)
       
        infh.close()

    df.to_json(path_to_input_json_file, orient='records')
