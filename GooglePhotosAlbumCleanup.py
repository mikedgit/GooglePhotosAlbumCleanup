import os
import time
import logging
import re
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import webbrowser
import pyautogui
import configparser
import platform
import pandas as pd

# Define a constant for the config file name
CONFIG_FILENAME = 'GooglePhotosAlbumCleanupConfig.ini'
# Global translation matrix for spreadsheet headers to what the script expects.  You can edit the headers here to match your spreadsheet.
LONG_TO_SHORT_HEADERS = {
    "Album Title": "Album Title",
    "Album New Title (Renamer will use this title)": "Album New Title",
    "Photo Count": "Photo Count",
    "Flagged for Deletion (Deleter will delete any album with the word ""TRUE"" in here)": "Delete Flag",
    "Album ID": "Album ID",
    "Album URL": "Album URL",
    "Actions Log": "Actions",
}
# Create an inverse of this dictionary for translating back
SHORT_TO_LONG_HEADERS = {v: k for k, v in LONG_TO_SHORT_HEADERS.items()}


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
        # Create a logger
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)

        # Create a file handler that logs messages to a file
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)

        # Create a console handler that logs messages to the console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)

        # Add handlers to the logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    except (configparser.NoSectionError, configparser.NoOptionError) as e:
        logging.error(f"Aborting. Failed to get log file parameter from config file {filename}: {e}")
        return False

    # Try to get the required parameters
    parameters = {}
    try:
        parameters['three_dots'] = tuple(map(float, config.get('AlbumWindowMouseClicks', 'three_dots').split(',')))
        parameters['macos_scale_factor'] = config.getfloat('AlbumWindowMouseClicks', 'macos_scale_factor')
        parameters['delete_button'] = tuple(map(float, config.get('AlbumDeleteMouseClicks', 'delete_button').split(',')))
        parameters['confirm_delete_button'] = tuple(map(float, config.get('AlbumDeleteMouseClicks', 'confirm_delete_button').split(',')))
        parameters['rename_button'] = tuple(map(float, config.get('AlbumRenameMouseClicks', 'rename_button').split(',')))
        parameters['rename_textbox'] = tuple(map(float, config.get('AlbumRenameMouseClicks', 'rename_textbox').split(',')))
        parameters['rename_save_button'] = tuple(map(float, config.get('AlbumRenameMouseClicks', 'rename_save_button').split(',')))
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

def read_xlsx_with_renamed_columns(file_path):
    """
    Reads a DataFrame from an XLSX file, renames columns, and logs errors for missing columns or file.

    :param file_path: Path to the XLSX file.
    :return: A pandas DataFrame with renamed columns or None if an error occurs.
    """
    # Check if the file exists
    if not os.path.exists(file_path):
        logging.error(f"File not found: {file_path}")
        return None

    # Read the XLSX file
    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        logging.error(f"Error reading the Excel file: {e}")
        return None

    # Check for missing expected columns
    missing_columns = set(LONG_TO_SHORT_HEADERS.keys()) - set(df.columns)
    if missing_columns:
        logging.error(f"Missing expected columns: {missing_columns}")
        return None

    # Rename columns
    df.rename(columns=LONG_TO_SHORT_HEADERS, inplace=True)
    return df

def write_xlsx_with_renamed_columns(df, output_file_path):
    """
    Writes the given DataFrame to an XLSX file. Overwrites the file if it already exists and logs the event.

    :param df: The DataFrame to write.
    :param output_file_path: The path to the output XLSX file.
    """

    # Check if the file already exists
    if os.path.exists(output_file_path):
        logging.info(f"Overwriting existing file: {output_file_path}")
    # Rename columns
    df.rename(columns=SHORT_TO_LONG_HEADERS, inplace=True)
    # Write DataFrame to an XLSX file
    df.to_excel(output_file_path, index=False)
    logging.info(f"Data written to {output_file_path}")


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

    # Initialize a dictionary to hold album data
    album_data = {'Album Title': [], 'Album New Title': [], 'Photo Count': [], 'Delete Flag': [], 'Album ID': [], 'Album URL': [], 'Actions': []}

    # Call the Photo v1 API
    logging.info('Polling Google Photos and Listing albums...If you have a lot, this may take a while.')
    page_token = None
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
                    albumId = album.get('id', 'No ID')
                    url = album.get('productUrl', 'No URL')
                    # Append album details to the dictionary
                    album_data['Album Title'].append(title)
                    album_data['Album New Title'].append('')  # Placeholder value
                    album_data['Photo Count'].append(mediaItemsCount)
                    album_data['Delete Flag'].append('')  # Placeholder value
                    album_data['Album ID'].append(albumId)
                    album_data['Album URL'].append(url)
                    album_data['Actions'].append('')  # Placeholder value
                except Exception as e:
                    logging.error(f"Error processing album: {e}")
        page_token = results.get('nextPageToken')
        # if len(album_data['Album Title']) > album_list_length_limit: 
        #     break
        if not page_token:
            break
        time.sleep(1) # Sleep for 1 second to avoid rate limiting
    # Convert the dictionary to a DataFrame
    df_albums = pd.DataFrame(album_data)
    # Ensure 'Album New Title' column is of type object (string)
    # df_albums['Album New Title'] = df_albums['Album New Title'].astype(str)
    return df_albums

def mark_albums_to_delete(album_list, delete_empty_albums, delete_albums_that_contain):
    # convert delete_albums_that_contain to a list if it's just a simple string
    if isinstance(delete_albums_that_contain, str):
        delete_albums_that_contain = [delete_albums_that_contain]
    for index, album in album_list.iterrows():
        # Find albums with no photos
        if delete_empty_albums and album['Photo Count'] == '0':
            album_list.at[index, 'Delete Flag'] = True
        # Find albums that contain any of the specified strings
        elif delete_albums_that_contain[0] and any(s in album['Album Title'] for s in delete_albums_that_contain):
            album_list.at[index, 'Delete Flag'] = True
        # Find albums with 'iPhoto Events' and a date in the name
        elif 'iPhoto Events' in album['Album Title'] and re.search(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b \d{1,2}, \d{4}', album['Album Title']):
            album_list.at[index, 'Delete Flag'] = True
        # Add your own criteria here!  Replace the 'False' with your own criteria
        elif False:
            album_list.at[index, 'Delete Flag'] = True
    return album_list

def delete_albums(album_list, max_albums_to_delete, macos_scale_factor, three_dots_coordinates, delete_coordinates, confirm_coordinates, page_load_wait_time=1.0, mouse_move_wait_time=1.0, mouse_click_wait_time=1.0):
    albums_deleted = 0
    if platform.system() == 'Darwin':  # Darwin is the name for the macOS operating system
        scale_factor = macos_scale_factor
    else:
        scale_factor = 1.0
    for index, album in album_list.iterrows():
        if bool(album['Delete Flag']) != True:
            continue
        if bool(album['Delete Flag']) == True and 'Deleted' in str(album['Actions']):
            continue
        if albums_deleted >= max_albums_to_delete:
            logging.info(f"Reached maximum number of albums to delete ({max_albums_to_delete}). Exiting.")
            break
        logging.info(f"Deleting album: {album['Album Title']} at {album['Album URL']}")
        # First let's open the web browser to the Google Photos Album page
        webbrowser.open(album['Album URL'])
        time.sleep(page_load_wait_time) # Sleep to allow the page to load
        # Now let's click the three dots at the top right of the page
        pyautogui.moveTo(three_dots_coordinates*scale_factor)
        time.sleep(mouse_move_wait_time)
        pyautogui.click(three_dots_coordinates*scale_factor)
        time.sleep(mouse_click_wait_time) # Sleep for 1 second to allow the menu to load
        # Now let's click the 'Delete' button
        pyautogui.moveTo(delete_coordinates*scale_factor)
        time.sleep(mouse_move_wait_time)
        pyautogui.click(delete_coordinates*scale_factor)
        time.sleep(mouse_click_wait_time)
        # Now let's confirm the deletion in the dialog box
        pyautogui.moveTo(confirm_coordinates*scale_factor)
        time.sleep(mouse_move_wait_time)
        pyautogui.click(confirm_coordinates*scale_factor)
        time.sleep(mouse_click_wait_time)
        album['Actions'] = ['Deleted on ' + time.strftime('%Y-%m-%d %H:%M:%S')]
        # Finally, lets close the web browser tab
        if platform.system() == 'Darwin':  # Darwin is the name for the macOS operating system
            pyautogui.hotkey('cmd', 'w')
        else:
            pyautogui.hotkey('ctrl', 'w')
        time.sleep(mouse_click_wait_time)
        albums_deleted += 1
        return album_list

def mark_albums_to_rename(album_list):
    for index, album in album_list.iterrows():
        # Find albums with 'Copy of 'in the name
        if 'Copy of ' in album['Album Title']:
            album_list.at[index, 'Album New Title'] = album['Album Title'].replace('Copy of ', '')
    return album_list

def rename_albums(album_list, max_albums_to_delete, three_dots, rename_button, rename_textbox, rename_save_button):
    return album_list

def main():
    # Read the configuration file into memory
    parameters = read_config_and_set_up_logging(CONFIG_FILENAME)
    if parameters == False:
        logging.error(f"Failed to read config file {CONFIG_FILENAME}. Exiting.")
        exit()

    while True:
        print("\nGoogle Photos Album Cleanup Menu:")
        print("1. Download the full album list from Google Photos and save to a file in the current directory")
        print("2. Modify the full album list from option 1 to generate a list of albums to RENAME based on script criteria")
        print("3. Use the full album list from option 1 to generate a list of albums to DELETE based on script criteria")
        print("4. Record mouse movements for deleting and renaming albums")
        print("5. Drive the mouse and rename albums based on the list of albums to rename")
        print("6. Drive the mouse and delete albums based on the list of albums to delete")
        print("Q. Quit")

        option = input("Please select an option: ")

        if option == '1':
            # Check if the file exists
            if os.path.exists(parameters['album_list_file']):
                # Ask the user if they want to overwrite the file
                overwrite = input('Album list file already exists. Do you want to overwrite it? (y/n): ')
                if overwrite.lower() != 'y':
                    print('File not overwritten. Going back to main menu.')
                    continue
            # Call the function to download the album list and write to a file
            album_list = google_photos_album_lister(parameters['scopes'], parameters['credentials_file'], parameters['token_file'], parameters['album_list_length_limit'])
            write_xlsx_with_renamed_columns(album_list, parameters['album_list_file'])
            print('The file can be further processed by the script in options 2 and 3, or you can edit the file yourself and use options 4, then 5 and 6.')
        elif option == '2':
            if not os.path.exists(parameters['album_list_file']):
                print('No album list file found. Please run option 1 first.')
                continue
            album_list = read_xlsx_with_renamed_columns(parameters['album_list_file'])
            album_list = mark_albums_to_rename(album_list)
            write_xlsx_with_renamed_columns(album_list, parameters['album_list_file'])

        elif option == '3':
            if not os.path.exists(parameters['album_list_file']):
                print('No album list file found. Please run option 1 first.')
                continue
            album_list = read_xlsx_with_renamed_columns(parameters['album_list_file'])
            album_list = mark_albums_to_delete(album_list, parameters['delete_empty_albums'], parameters['delete_albums_that_contain'])
            write_xlsx_with_renamed_columns(album_list, parameters['album_list_file'])

        elif option == '4':
            # Assuming MouseClickFinderScript.py is in the same directory and has a main() function
            import MouseClickFinderScript
            MouseClickFinderScript.main()

        elif option == '5':
            confirm = input('You will not be able to use your computer during this time. Continue? (y/n): ')
            if confirm.lower() != 'y':
                continue
            album_list = read_xlsx_with_renamed_columns(parameters['album_list_file'])
            album_list = rename_albums(album_list, parameters['max_albums_to_delete'], parameters['three_dots'], parameters['rename_button'], parameters['rename_textbox'], parameters['rename_save_button'])
            write_xlsx_with_renamed_columns(album_list, parameters['album_list_file'])

        elif option == '6':
            confirm = input('You will not be able to use your computer during this time. Continue? (y/n): ')
            if confirm.lower() != 'y':
                continue
            album_list = read_xlsx_with_renamed_columns(parameters['album_list_file'])
            album_list = delete_albums(album_list, parameters['max_albums_to_delete'], parameters['macos_scale_factor'], parameters['three_dots'], parameters['delete_button'], parameters['confirm_delete_button'])
            write_xlsx_with_renamed_columns(album_list, parameters['album_list_file'])
        elif option.lower() == 'q':
            break
        else:
            print("Invalid option. Please try again.")

if __name__ == "__main__":
    main()