import logging


# Example with one serie:
# SERIES = [
#    {
#        "season": 1, 
#        "episode": 10, 
#        "name": "Breaking Bad", 
#        "hd": 1
#    }, 
# ]
#
# 'name' should be the exact, case-sensitive, tv show title
# If 'hd' is set to 0, or not set, only low quality will be downloaded
# If 'hd' is set to 1 only 720p (HD) episodes will be downloaded
#
# ** DON'T REMOVE <STATE> </STATE> LABELS **
# because this block is re-used as JSON-based persistent storage :)
#
# <STATE>
SERIES = [
]
# </STATE>

SUBTITLES_PATH = '' # Leave blank if you don't want subtitles to be downloaded
SUBTITLES_LANGUAGE = 'English'
TORRENT_WATCH_PATH = ''
TPB_TRUSTED_USERS = ['eztv', 'DibyaTPB', 'Drarbg']
LOG_LEVEL = logging.DEBUG

EMAIL_USER = '' # Leave blank if you don't want email alerts
EMAIL_PASSWORD = ''
EMAIL_RECIPIENTS = []
EMAIL_SMTP_HOST = ''
EMAIL_SMTP_PORT = 25
