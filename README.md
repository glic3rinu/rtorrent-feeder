rtorrent-feeder
===============

Automatically downloads magnets from EZRSS and The Pirate Bay

**This script is intended to work with [rtorrent](http://libtorrent.rakshasa.no/)**

The following functionality is provided:
 * Downloads TV show magnets using [EZRSS](http://ezrss.it/) as primary source and [TPB](http://thepiratebay.se) as failback
 * Downloads subtitles from [Addic7ed](http://www.addic7ed.com/)
 * Sends email alerts
 * Allows quality to be specified (720p or low)


Installation
------------
1. Drop the script on your system
2. Configure it
3. Create a similar crontab entry for periodic execution: <pre><code>*/5 * * * * python /home/rt/rtorrent-feeder.py</code></pre>


Configuration Example
---------------------

    # <CONFIG>
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
    # </CONFIG>
    
    SUBTITLES_PATH = '/media/data/subtitles/'
    TORRENT_WATCH_PATH = '~/TorrentsToWatch/'
    
    EMAIL_USER = 'youremail@example.com'
    EMAIL_PASSWORD = 'randompassword'
    EMAIL_RECIPIENTS = ['listofpeople@to-notify.com']
    EMAIL_SMTP_SERVER = 'smtp.your-host.com'
    EMAIL_SMTP_PORT = 25
