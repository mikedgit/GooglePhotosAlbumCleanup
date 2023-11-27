import time
from pynput.mouse import Listener
import webbrowser
import configparser

# Define a constant for the config file name
CONFIG_FILENAME = 'GooglePhotosAlbumCleanupConfig.ini'

listening = False
click_coordinates = []

def on_click(x, y, button, pressed):
    global listening
    if listening and pressed:
        print('Mouse clicked at ({0}, {1})'.format(x, y))
        click_coordinates.append(('category','tag', x, y))
        listening = False  # Turn off listening

def prompt_to_memorize_coordinates(coordinate_category, coordinate_tag, prompt):
    global listening
    listening = True
    while True:
        print(
"""\nPlease note the very next click will be the one recorded.
If you click somewhere else (say to select the browser window), you will have to start over.
It's recommended to use alt-tab on windows or command-tab on mac to switch to the browser window.\n""")
        print(prompt)
        while listening:
            time.sleep(0.1)  # Sleep for a short time to prevent high CPU usage
        # Label the coordinates with the tag
        click_coordinates[-1] = (coordinate_category, coordinate_tag, click_coordinates[-1][2], click_coordinates[-1][3])
        print(f'Click recorded as {click_coordinates[-1]}')
        response = input('\nWas that the click you wanted? ("y" for yes, "c" to cancel, and anything else for "no keep monitoring"):\n')
        if response.lower() == 'y':
            return True
        elif response.lower() == 'c':
            # Delete the last coordinates
            click_coordinates.pop()
            return False
        else:
            # Delete the last coordinates
            click_coordinates.pop()
            print('Ok, try again.')
            listening = True

def update_config_file(config_filename):
    config = configparser.ConfigParser()
    config.read(config_filename)
    # Iterate over the click_coordinates list
    for coordinate in click_coordinates:
        # Extract the category, tag, and coordinates
        category, tag, x, y = coordinate
        # Update the coordinates in the config file
        config.set(category, tag, f'{x}, {y}')
    # Write the changes back to the file
    with open(config_filename, 'w') as configfile:
        config.write(configfile)

def main():
    global listening
    listening = False
    with Listener(on_click=on_click) as listener:
        response = input(
"""\nWould you like to record mouse clicks so you can use the album delete function?
("y" for yes, and anything else to skip)\n""")
        if response.lower() == 'y':
            print(
"""\nI will perform the following steps:
1) Open your system default web browser
2) Open photos.google.com"""                
            )
            time.sleep(3)
            webbrowser.open('https://photos.google.com')
            response = input(
"""\nYou will need to perform the following steps:
3) Make sure you are logged in to your Google account
4) Click on the Albums tab and open an album you can delete (make a new one if you don't have one).

When you're ready, click here on the Python console then ("y" for yes, and anything else to skip) and press <enter> when ready.""")
            if response.lower() == 'y':
                if prompt_to_memorize_coordinates('AlbumWindowMouseClicks','three_dots', 'Recording location of next click.\nPlease click the three dots at the top right of the album page you just opened.'):
                    if prompt_to_memorize_coordinates('AlbumDeleteMouseClicks','delete_button', 'Please click the "Delete Album" menu item.'):
                        if prompt_to_memorize_coordinates('AlbumDeleteMouseClicks','confirm_delete_button', 'Please click the "Delete" button in the confirmation dialog.'):
                            print('Great! Now we will save those coordinates.')
                            update_config_file(CONFIG_FILENAME)
                        else:
                            print('Ok, we will skip saving the coordinates.')
                    else:
                        print('Ok, we will skip saving the coordinates.')                        
                else:
                    print('Ok, we will skip saving the coordinates.')
        else:
            print('Ok, we will skip saving the delete coordinates.')
        
        response = input(
"""\nWould you like to record mouse clicks so you can use the album rename function?
("y" for yes, and anything else to skip)""")
        if response.lower() == 'y':
            print(
"""\nI will perform the following steps:
1) Open your system default web browser
2) Open photos.google.com"""                
            )
            time.sleep(3)
            webbrowser.open('https://photos.google.com')          
            response = input(
"""\nYou will need to perform the following steps:
3) Make sure you are logged in to your Google account
4) Click on the Albums tab and open an album you can rename (make a new one if you don't have one).

When you're ready, click here on the Python console then ("y" for yes, and anything else to skip) and press <enter> when ready.""")
            if response.lower() == 'y':
                if prompt_to_memorize_coordinates('AlbumWindowMouseClicks','three_dots', 'Recording location of next click.\nPlease click the three dots at the top right of the album page you just opened.'):
                    if prompt_to_memorize_coordinates('AlbumRenameMouseClicks','rename_button', 'Please click the "Edit album" menu item.'):
                        if prompt_to_memorize_coordinates('AlbumRenameMouseClicks','rename_textbox', 'Please click the album name field at or near the beginning.'):
                            if prompt_to_memorize_coordinates('AlbumRenameMouseClicks','rename_save_button', 'Please click the checkmark button at the top left of the screen (confirms edit).'):
                                print('Great! Now we will save those coordinates.')
                                update_config_file(CONFIG_FILENAME)
                            else:
                                print('Ok, we will skip saving the coordinates.')
                        else:
                            print('Ok, we will skip saving the coordinates.')
                    else:
                        print('Ok, we will skip saving the coordinates.')                        
                else:
                    print('Ok, we will skip saving the coordinates.')
        else:
            print('Ok, we will skip saving the rename coordinates.')
        

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProgram stopped by user.")