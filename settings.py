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
    {
        "season": 2, 
        "episode": 8, 
        "name": "The Blacklist", 
        "hd": 1
    }, 
    {
        "season": 1, 
        "episode": 8, 
        "name": "True Detective", 
        "hd": 1
    }, 
    {
        "season": 2, 
        "episode": 13, 
        "name": "House of Cards", 
        "hd": 1
    }, 
    {
        "season": 4, 
        "episode": 9, 
        "name": "Person of Interest", 
        "hd": 1
    }, 
    {
        "season": 4, 
        "episode": 10, 
        "name": "Homeland", 
        "hd": 1
    }, 
    {
        "season": 1, 
        "episode": 13, 
        "name": "Almost Human", 
        "hd": 1
    }, 
    {
        "season": 4, 
        "episode": 10, 
        "name": "Game of Thrones", 
        "hd": 1
    }, 
    {
        "season": 3, 
        "episode": 3, 
        "name": "Sherlock", 
        "hd": 1
    }, 
    {
        "season": 2, 
        "episode": 3, 
        "name": "Black Mirror", 
        "hd": 1
    }, 
    {
        "season": 3, 
        "episode": 24, 
        "name": "Elementary"
    }, 
    {
        "season": 2, 
        "episode": 13, 
        "name": "Hannibal", 
        "hd": 1
    }, 
    {
        "season": 6, 
        "episode": 22, 
        "name": "The Mentalist"
    }, 
    {
        "season": 7, 
        "episode": 23, 
        "name": "Castle 2009"
    }, 
    {
        "season": 1, 
        "episode": 13, 
        "name": "Helix", 
        "hd": 1
    }, 
    {
        "season": 1, 
        "episode": 11, 
        "name": "Rick and Morty", 
        "hd": 1
    }, 
    {
        "season": 1, 
        "episode": 22, 
        "name": "Psycho-Pass", 
        "hd": 1
    }, 
    {
        "season": 1, 
        "episode": 25, 
        "name": "Attack on Titan", 
        "hd": 1
    }, 
    {
        "season": 1, 
        "episode": 13, 
        "name": "Cosmos A Space Time Odyssey", 
        "hd": 1
    }, 
    {
        "season": 1, 
        "episode": 10, 
        "name": "Fargo", 
        "hd": 1
    }, 
    {
        "season": 1, 
        "episode": 10, 
        "name": "The Leftovers", 
        "hd": 1
    }, 
    {
        "season": 1, 
        "episode": 8, 
        "name": "Silicon Valley", 
        "hd": 1
    }, 
    {
        "season": 2, 
        "episode": 10, 
        "name": "Banshee", 
        "hd": 1
    }, 
    {
        "season": 1, 
        "episode": 8, 
        "name": "Outlander", 
        "hd": 1
    }, 
    {
        "season": 2, 
        "episode": 13, 
        "name": "Orange Is The New Black", 
        "hd": 1
    }
]
# </STATE>

SUBTITLES_PATH = '/media/data/subtitles/'
SUBTITLES_LANGUAGE = 'English'
TORRENT_WATCH_PATH = '~/TorrentsToWatch/'
TPB_TRUSTED_USERS = ['eztv', 'DibyaTPB', 'Drarbg']
LOG_LEVEL = logging.INFO

EMAIL_USER = 'media@calmisko.org'
EMAIL_PASSWORD = 'Xbr5AW&E'
EMAIL_RECIPIENTS = ['ladycrazy@gmail.com', 'glicerinu@gmail.com']
EMAIL_SMTP_HOST = 'smtp.gmail.com'
EMAIL_SMTP_PORT = 587

