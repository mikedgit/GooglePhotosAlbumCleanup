# Readme for GooglePhotosAlbumCleanup Script

# Google Photos Album Cleanup
**WARNING**: I consider this an advanced script to use.  Please **PAY ATTENTION** to the instructions here, or you may have some very sad outcomes like deleted albums that you don’t want to delete, or random button clicks on your screen that won’t stop and do unpredictable things.  Don’t say I didn’t warn you.  That said, if you follow the instructions, I’ve found it worked REALLY well for me to clean up a very messed up Google Photos situation I got myself into.
## The Messed Up Google Photos Situation
This all came about because I had migrated from iCloud Photos to Google Photos, and my iCloud Photos had THOUSANDS of automatically created photo albums from a long time ago.  These photo albums were helpfully duplicated in my Google Photos library.  I realized to my shock that there was NO WAY to delete Google Photo Albums unless you did it MANUALLY through the web browser.  In my case, working monotonously for 5 hours would have deleted all of the albums I needed.  Forget that!  Instead I’ll spend 15 hours working on an automatic way to do it!  This script is the result.
## Overview
Google Photos Album Cleanup is an open-source Python project designed to automate the management and cleanup of Google Photos albums.  It can:
- List the albums you have in a markdown file with a table so you can review them.
- Run your web browser to delete any albums based on criteria you set in Python.  Alternatively, you can edit the markdown table to create a list of albums to delete.
- (Near-Future feature) Run your web browser to rename albums based on criteria you set in Python.  Alternatively, you can edit the markdown table to create a list of albums to rename.
## Methodology
- Recording your mouse clicks as you navigate your default browser in Google Photos to learn where to click, for both deleting and renaming.
- Using the `GooglePhotosAlbumCleanup.ini` config file to know what you want it to do.
- Downloading the list of albums from Google with the Google Photos API
- Making a list of albums to delete or rename based on configuration -or- Python code
- Using that list to open each album one at a time in your browser and perform the functions as if you were doing it
## Features
- Automated cleanup of Google Photos albums.
- Automated mouse interactions using the Mouse Click Finder.
## Prerequisites
- A Gmail or Google Workspace account with Google Photos
- Access to the Google Developer’s Console (hint: if you have gmail, this should just work.  If you have a Google Workspace account (i.e. your email ends with something other than gmail.com), then you may need to log into the admin console (admin.google.com) and enable this feature for your account
- Python 3.x
- Dependencies listed in `requirements.txt`.
- API credentials from Google Photos (instructions below)
- Give python3 permission to screen record your Mac.
## Installation
1. Clone the repository: `git clone https://github.com/mikedgit/GooglePhotosAlbumCleanup.git`
2. Navigate to the project directory: `cd GooglePhotosAlbumCleanup`
3. (Optional) Create a virtual environment
   - For Windows: `python -m venv venv`
   - For Mac: `python3 -m venv venv`
4. (Optional) Activate the Virtual Environment
   - On Windows: `.\venv\Scripts\activate`
   - On macOS and Linux: `source venv/bin/activate`
5. Install required dependencies: `pip install -r requirements.txt`
## API Key from Google
In order to download lists and organize your Google Photos album, we're going to employ the [Google Photos API](https://developers.google.com/photos/library/guides/overview).
You will need to obtain a client_secret JSON file from the Google Cloud Platform Console.  Here’s the procedure as of the writing of this readme:
1. Create a Google Cloud Project:
   - Go to the Google Cloud Platform Console: ~[https://console.developers.google.com/](https://console.developers.google.com/)~.
   * If you haven't already, create a Google Cloud project.
   * Select the project you want to use for accessing the Google Photos API.
2. Enable the Google Photos Library API:
   * From the left-hand menu, navigate to "APIs & Services" > "Library".
   * Search for "Google Photos Library API" and click "Enable".
3. Create OAuth Client ID:
   * From the left-hand menu, navigate to "APIs & Services" > "Credentials".
   * Click "Create Credentials" > "OAuth client ID".
   * Select "Web application" as the application type.
   * Enter a descriptive name for your application (e.g., "My Photos App").
   * Click "Create".
4. Download Credentials File:
   * A dialog box will appear with your Client ID and Client Secret.
   * Click "Download JSON" to download the credentials file (named `client_secret.json`).
   * This file contains all the necessary information to authenticate your application with the Google Photos API.
5. Save in your project directory and store securely:
   * Store the `client_secret.json` file securely, as it contains sensitive information.  It is excluded explicitly in the `.gitignore` file in the project directory.  You don’t want to accidentally put that online!
## Usage
### Google Photos Album Cleanup
1. Configure `GooglePhotosAlbumCleanupConfig.ini` with your preferences.
2. Run the script: `python GooglePhotosAlbumCleanup.py` (Windows) or `python3 GooglePhotosAlbumCleanup.py` (MacOS)

### Mouse Click Finder
1. Run the script: `python MouseClickFinderScript.py`
2. Follow the on-screen instructions to find and record mouse clicks.

## Configuration
Edit the `GooglePhotosAlbumCleanupConfig.ini` file to customize the cleanup process according to your needs.

## Contributing
Contributions are welcome! Please read our contributing guidelines to get started.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments
- Thanks to all contributors and users of this project.
- **Not Perfect**: This script is not perfect.  There are quite a few ways I could improve it (and I’m sure you could think of them too).  If you want something to change, [log an issue in Github](https://github.com/mikedgit/GooglePhotosAlbumCleanup/issues) or make the change and [submit a pull request](https://github.com/mikedgit/GooglePhotosAlbumCleanup/pulls).