rtorrent-feeder
===============

This is a fairly simple Python script for automatically download magnets from [Kickass Torrents](https://kickass.so/), [EZRSS](http://ezrss.it/) and [The Pirate Bay](http://thepiratebay.se). It has been written for [rtorrent](http://libtorrent.rakshasa.no/) but it will work with any other client that is just able to _watch on a folder_ for new torrents.
 * Download TV show magnets from [Kickass Torrents](https://kickass.so/), [EZRSS](http://ezrss.it/) and [TPB](http://thepiratebay.se) via RSS
 * Optional downloading of subtitles from [Addic7ed](http://www.addic7ed.com/)
 * Optional email alerts of new downloads
 * Allows quality to be specified (720p or low)


Installation
------------
0. Make sure you have Python >= 2.6
1. Clone this repo:
    ```bash
    cd /home/rt/ && git clone https://github.com/glic3rinu/rtorrent-feeder.git
    ```

2. Create a new config file `cp settings.py.example settings.py` and [`settings.py`](edit it).
3. Add a similar crontab entry for periodic execution:

    ```bash
    */10 * * * * cd /home/rt && python -m rtorrent-feeder.main
    ```



Configuration Example
---------------------
```python
# <STATE>
SERIES = [
    {
        "season": 1, 
        "episode": 10, 
        "name": "The Blacklist", 
    }, 
    {
        "season": 1, 
        "episode": 13, 
        "name": "House of Cards", 
        "hd": 1
    }, 
    {
        "season": 3, 
        "episode": 11, 
        "name": "Person of Interest", 
        "hd": 1
    }
]
# </STATE>

SUBTITLES_PATH = '/media/data/subtitles/'
SUBTITLES_LANGUAGE = 'English'
TORRENT_WATCH_PATH = '~/TorrentsToWatch/'
TPB_TRUSTED_USERS = ['eztv', 'DibyaTPB']
LOG_LEVEL = logging.INFO

EMAIL_USER = 'randomaddress@gmail.com'
EMAIL_PASSWORD = 'randompassword'
EMAIL_RECIPIENTS = ['randomaddress@gmail.com']
EMAIL_SMTP_SERVER = 'smtp.gmail.com'
EMAIL_SMTP_PORT = 587
```
