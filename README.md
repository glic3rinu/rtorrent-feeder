rtorrent-feeder
===============

This is a fairly simple Python tool for automatically download magnets from [Kickass Torrents (RSS)](https://kickass.so/), [EZRSS (RSS)](http://ezrss.it/) and [The Pirate Bay (RSS and HTML)](http://thepiratebay.se). It has been written for [rtorrent](http://libtorrent.rakshasa.no/) but it will work with any other client that is just able to _watch on a folder_ for new torrents.
 * Download TV show magnets from [Kickass Torrents](https://kickass.so/), [EZRSS](http://ezrss.it/) and [TPB](http://thepiratebay.se) via RSS and/or HTML
 * Optional downloading of subtitles from [Addic7ed](http://www.addic7ed.com/)
 * Optional email alerts of new downloads
 * Allows quality to be specified (`'lo'`, `'hd'`, `'1080p'` or `'720p'`)
 * Easily enable/disable specific feeders with a setting variable
 * Has support for running functions after events ([signals](#signals))


**At this time ThePirateBay and EZRSS have their RSS feeds down**

Installation
------------
0. Make sure you have Python >= 2.6
1. Clone this repo:
    ```bash
    cd /home/rt/ && git clone https://github.com/glic3rinu/rtorrent-feeder.git
    ```

2. Create a new config file `cp settings.py.example settings.py` and [`edit it`](#configuration-example).
3. Add a similar crontab entry for periodic execution:

    ```bash
    */10 * * * * cd /home/rt && python -m rtorrent-feeder.main
    ```



Configuration Example
---------------------
```python
SERIES = [
    {
        "season": 1, 
        "episode": 10, 
        "name": "The Blacklist"
    }, 
    {
        "season": 1, 
        "episode": 13, 
        "name": "House of Cards", 
        "quality": '1080p'
    }, 
    {
        "season": 3, 
        "episode": 11, 
        "name": "Person of Interest", 
        "quality": 'hd'
    }
]

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

FEEDERS = [
    'rtorrent-feeder.downloaders.KickAssDownloader',
    'rtorrent-feeder.downloaders.TPBHTMLDownloader',
#   'rtorrent-feeder.downloaders.TPBDownloader',
#   'rtorrent-feeder.downloaders.EZRSSDownloader',
]

if SUBTITLES_PATH:
    FEEDERS.append('rtorrent-feeder.downloaders.Addic7edDownloader')
```


Signals
-------
Support for registering functions to be executed after a torrent/subtitle download is performed is provided by `downloaders.post_download` signal.

For using it, you can create a `signals.py` file inside rtorrent-feeder directory with your function and register it with `downloaders.post_download.connect()`.

For example:

```python
# signals.py

import subprocess
from . import utils, downloaders

def send_subtitles_home(sender, serie, s, e, filename):
    standard_filename = utils.standardize(filename, serie, s, e)
    scp_cmd = 'scp "{filename}" user@home:/media/subtitles/{standard_filename}'
    scp_cmd = scp_cmd.format(filename=filename, standard_filename=standard_filename)
    subprocess.call(scp_cmd, shell=True)

downloaders.post_download.connect(
    send_subtitles_home, senders=[downloaders.Addic7edDownloader])
```

If you are using rtorrent and you want actions to be executed after a torrent download is completed you can use rtorrent built-in event system. For example:

```
# .rtorrent.rc
system.method.set_key = event.download.finished,sync_serie,"execute=ssh,root@calmisko.org,/home/rt/sync,$d.get_base_path="
```
