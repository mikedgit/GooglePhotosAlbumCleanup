import os
import time
import logging
import re
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from tabulate import tabulate
import webbrowser
import pyautogui
import configparser
import platform

# Define a constant for the config file name
CONFIG_FILENAME = 'GooglePhotosAlbumCleanupConfig.ini'

def read_config_and_set_up_logging(filename):
    # Create a ConfigParser object
    config = configparser.ConfigParser()

    # Try to read the config file
    try:
        config.read(filename)
    except configparser.Error as e:
        logging.basicConfig(filename='error.log', level=logging.ERROR)
        logging.error(f"Failed to read config file {filename}: {e}")
        return False

    # Try to get the log file parameter first and set up logging
    try:
        log_file = config.get('logging', 'file')
        # Clear the previous log
        with open(log_file, 'w'):
            pass
        # Set up logging
        logging.basicConfig(filename=log_file, level=logging.INFO)
    except (configparser.NoSectionError, configparser.NoOptionError) as e:
        logging.error(f"Aborting. Failed to get log file parameter from config file {filename}: {e}")
        return False

    # Try to get the required parameters
    parameters = {}
    try:
        parameters['three_dots'] = tuple(map(int, config.get('AlbumWindowMouseClicks', 'three_dots').split(',')))
        parameters['delete_button'] = tuple(map(int, config.get('AlbumDeleteMouseClicks', 'delete_button').split(',')))
        parameters['confirm_delete_button'] = tuple(map(int, config.get('AlbumDeleteMouseClicks', 'confirm_delete_button').split(',')))
        parameters['rename_button'] = tuple(map(int, config.get('AlbumRenameMouseClicks', 'rename_button').split(',')))
        parameters['rename_textbox'] = tuple(map(int, config.get('AlbumRenameMouseClicks', 'rename_textbox').split(',')))
        parameters['rename_save_button'] = tuple(map(int, config.get('AlbumRenameMouseClicks', 'rename_save_button').split(',')))
        parameters['album_list_file'] = config.get('AlbumLister', 'album_list_file')
        parameters['album_list_length_limit'] = config.getint('AlbumLister', 'album_list_length_limit')
        parameters['albums_to_delete_list_file'] = config.get('AlbumDeleteLister', 'albums_to_delete_list_file')
        parameters['delete_empty_albums'] = config.getboolean('AlbumDeleteLister', 'delete_empty_albums')
        parameters['delete_albums_that_contain'] = tuple(map(str, config.get('AlbumDeleteLister', 'delete_albums_that_contain').split(',')))
        parameters['delete_albums'] = config.getboolean('AlbumDeleter', 'delete_albums')
        parameters['max_albums_to_delete'] = config.getint('AlbumDeleter', 'max_albums_to_delete')
        parameters['page_load_wait_time'] = config.getfloat('AlbumDeleter', 'page_load_wait_time')
        parameters['mouse_move_wait_time'] = config.getfloat('AlbumDeleter', 'mouse_move_wait_time')
        parameters['mouse_click_wait_time'] = config.getfloat('AlbumDeleter', 'mouse_click_wait_time')
        parameters['scopes'] = config.get('GooglePhotosAPI', 'scopes')
        parameters['credentials_file'] = config.get('GooglePhotosAPI', 'credentials_file')
        parameters['token_file'] = config.get('GooglePhotosAPI', 'token_file')
    except (configparser.NoSectionError, configparser.NoOptionError) as e:
        logging.error(f"Failed to get a parameter from config file {filename}: {e}")
        return False

    return parameters

def google_photos_album_lister(scope, credentials_file, token_file, album_list_length_limit):
    # Define the scope for the access request
    SCOPES = [scope]

    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists(token_file):
        try:
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)
        except Exception as e:
            logging.error(f"Error using token file to authorize: {e}")

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(token_file, 'w') as token:
            token.write(creds.to_json())

    # Build the Google Photos API service
    # Note: static_discovery=False is required to avoid an error
    service = build('photoslibrary', 'v1', credentials=creds,static_discovery=False)

    # Call the Photo v1 API
    logging.info('Polling Google Photos and Listing albums...')
    page_token = None
    album_list = []
    page_count = 0
    while True:
        try:
            results = service.albums().list(pageSize=50, pageToken=page_token, excludeNonAppCreatedData=False).execute()
            albums = results.get('albums', [])
        except Exception as e:
            logging.error(f"Error listing albums: {e}")
            break
        if not albums:
            logging.info('No albums found.')
        else:
            page_count += 1
            logging.info(f"Page {page_count} of albums found (up to 50 albums per page)")
            for album in albums:
                try:
                    title = album.get('title', 'Untitled')
                    mediaItemsCount = album.get('mediaItemsCount', 0)
                    is_shared = 'shareInfo' in album
                    albumId = album.get('id', 'No ID')
                    url = album.get('productUrl', 'No URL')
                    album_list.append([title, mediaItemsCount, is_shared, albumId, url])
                except Exception as e:
                    logging.error(f"Error processing album: {e}")
        page_token = results.get('nextPageToken')
        if len(album_list) > album_list_length_limit: 
            break
        if not page_token:
            break
        time.sleep(1) # Sleep for 1 second to avoid rate limiting
    return album_list

def read_album_list_from_file(filename):
    with open(filename, 'r') as f:
        # Skip the first line (headers)
        next(f)
        # Read the rest of the lines into a list
        table = [line.strip().split('|') for line in f]
    # Remove the first and last elements of each list (the pipe characters)
    for row in table:
        row.pop(0)
        row.pop()
    return table

def find_albums_to_delete(album_list, delete_empty_albums, delete_albums_that_contain):
    albums_to_delete = []
    # convert delete_albums_that_contain to a list if it's just a simple string
    if isinstance(delete_albums_that_contain, str):
        delete_albums_that_contain = [delete_albums_that_contain]
    for album in album_list:
        # Find albums with no photos
        if delete_empty_albums and album[1] == '0':
            albums_to_delete.append(album)
        # Find albums that contain any of the specified strings
        elif delete_albums_that_contain[0] and any(s in album[0] for s in delete_albums_that_contain):
            albums_to_delete.append(album)            
        # Find albums with 'iPhoto Events' and a date in the name
        elif 'iPhoto Events' in album[0] and re.search(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b \d{1,2}, \d{4}', album[0]):
            albums_to_delete.append(album)
        # Add your own criteria here!  Replace the 'False' with your own criteria
        elif False:
            albums_to_delete.append(album)
        # # Find albums with 'iPhoto Events' and a date in the name
        # elif 'iPhoto Events' in album[0] and re.search(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b \d{1,2}, \d{4}', album[0]):
        #     albums_to_delete.append(album)
    return albums_to_delete

def delete_albums(albums_to_delete, max_albums_to_delete, three_dots_coordinates, delete_coordinates, confirm_coordinates, page_load_wait_time=1.0, mouse_move_wait_time=1.0, mouse_click_wait_time=1.0):
    albums_deleted = 0
    for album in albums_to_delete:
        if albums_deleted >= max_albums_to_delete:
            logging.info(f"Reached maximum number of albums to delete ({max_albums_to_delete}). Exiting.")
            break
        logging.info(f"Deleting album: {album[0]} at {album[4]}")
        # First let's open the web browser to the Google Photos Album page
        webbrowser.open(album[4])
        time.sleep(page_load_wait_time) # Sleep to allow the page to load
        # Now let's click the three dots at the top right of the page
        pyautogui.moveTo(three_dots_coordinates)
        time.sleep(mouse_move_wait_time)
        pyautogui.click(three_dots_coordinates)
        time.sleep(mouse_click_wait_time) # Sleep for 1 second to allow the menu to load
        # Now let's click the 'Delete' button
        pyautogui.moveTo(delete_coordinates)
        time.sleep(mouse_move_wait_time)
        pyautogui.click(delete_coordinates)
        time.sleep(mouse_click_wait_time)
        # Now let's confirm the deletion in the dialog box
        pyautogui.moveTo(confirm_coordinates)
        time.sleep(mouse_move_wait_time)
        pyautogui.click(confirm_coordinates)
        time.sleep(mouse_click_wait_time)
        # Finally, lets close the web browser tab
        if platform.system() == 'Darwin':  # Darwin is the name for the macOS operating system
            pyautogui.hotkey('cmd', 'w')
        else:
            pyautogui.hotkey('ctrl', 'w')
        time.sleep(mouse_click_wait_time)
        albums_deleted += 1
        
def find_albums_to_rename(album_list):
    albums_to_rename = []
    for album in album_list:
        # Find albums with 'Copy of 'in the name
        if 'Copy of ' in album[0]:
            album.append(album[0].replace('Copy of ', ''))
            albums_to_rename.append(album)
    return albums_to_rename

def main():
    # Read the configuration file into memory
    parameters = read_config_and_set_up_logging(CONFIG_FILENAME)
    if parameters == False:
        logging.error(f"Failed to read config file {CONFIG_FILENAME}. Exiting.")
        exit()
    
    # If the album list markdown file doesn't exist, create it by calling the Google Photos API
    if not os.path.exists(parameters['album_list_file']):
        album_list = google_photos_album_lister(parameters['scopes'], parameters['credentials_file'], parameters['token_file'], parameters['album_list_length_limit'])
        table = tabulate(album_list, headers=['Album Title','Number of Photos','Sharing','Album ID','URL'], tablefmt='pipe')
        with open(parameters['album_list_file'], 'w') as f:
            f.write(table)
        logging.info('Created new album list markdown file.')
    # Otherwise, read the album list markdown file
    else:
        logging.info('Album list file already exists.  Not creating a new one.')
        album_list = read_album_list_from_file(parameters['album_list_file'])

    # Find the albums to delete based on criteria in the find_albums_to_delete function
    albums_to_delete = find_albums_to_delete(album_list, parameters['delete_empty_albums'], parameters['delete_albums_that_contain'])

    # If there are no albums to delete, exit
    if not albums_to_delete:
        logging.info('No albums to delete.')
        exit()
    # Otherwise, write the list of albums to delete to a markdown file
    else:
        table = tabulate(albums_to_delete, headers=['Album Title','Number of Photos','Sharing','Album ID','URL'], tablefmt='pipe')
        with open(parameters['albums_to_delete_list_file'], 'w'):
            pass
        logging.info('Cleared previous markdown file of albums to delete.')
        with open(parameters['albums_to_delete_list_file'], 'w') as f:
            f.write(table)
        logging.info('Created markdown file of albums to delete.')

    # Delete the albums
    if parameters['delete_albums']:
        delete_albums(albums_to_delete, parameters['max_albums_to_delete'], parameters['three_dots'], parameters['delete_button'], parameters['confirm_delete_button'])

if __name__ == "__main__":
    main()