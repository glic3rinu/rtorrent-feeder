import os
import re
import json
import subprocess
import urllib
import xml.etree.ElementTree as ET
import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText


# The following CONFIG block will be used as JSON-based persistent storage
# ** DON'T REMOVE THE LABELS <CONFIG> </CONFIG> **
#
# 'name' should be the exact tv show title, and is case-sensitive
# If 'hd' is set to 1 only 720p (HD) episodes will be downloaded
#
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
EMAIL_SMTP_HOST = 'smtp.your-host.com'
EMAIL_SMTP_PORT = 25


def download_magnet(item, match, season, episode, serie):
    """ Downloads item's magnet if match is a new episode """
    s, e = [ int(e) for e in match.groups() ]
    if s > 19: # Workaround to some wrongly labeled episodes
        return
    if s > season or (s == season and e > episode):
        torrent = '{http://xmlns.ezrss.it/0.1/}torrent'
        magnetURI = '{http://xmlns.ezrss.it/0.1/}magnetURI'
        magnet = item.find(torrent).find(magnetURI).text
        context = {
            'magnet': magnet,
            'torrent_watch_path': TORRENT_WATCH_PATH
        }
        subprocess.call(
            'MAGNET="%(magnet)s"; \n'
            'cd %(torrent_watch_path)s; \n'
            '[[ "$MAGNET" =~ xt=urn:btih:([^&/]+) ]] || exit; \n'
            'echo "d10:magnet-uri${#MAGNET}:${MAGNET}e"'
            ' > "meta-${BASH_REMATCH[1]}.torrent"; \n'
            % context, shell=True, executable='/bin/bash')
        title = item.find('title').text
        downloads.append((title, serie))
        serie['season'] = max(serie['season'], s)
        serie['episode'] = max(serie['episode'], e)


downloads = []


# Download magnets from EZRSS
url = 'http://ezrss.it/search/index.php'
for serie in SERIES:
    # Construct URL query
    name = serie['name'].replace(' ', '+')
    if serie.get('hd', 0):
        quality = 'quality=720p'
    else:
        quality = 'quality=HDTV&quality_exact=true'
    query = 'show_name=%s&show_name_exact=true&%s&mode=rss' % (name, quality)
    try:
        ezrss = urllib.urlopen(url + '?' + query)
    except IOError:
        break
    if ezrss.getcode() != 200:
        continue
    # Search for new episodes to download
    ezrss = ET.parse(ezrss)
    regex = '.* Season: (\d+); Episode: (\d+)$'
    season, episode = serie['season'], serie['episode']
    for item in ezrss.getroot()[0].findall('item'):
        description = item.find('description').text
        match = re.match(regex, description)
        download_magnet(item, match, season, episode, serie)


# Download magnets from The Pirate Bay (eztv and PublicHD)
feeds = {}
for serie in SERIES:
    # Construct regular expression and select quality feed
    # TODO 'trust mechanism' based on user rather than perfect title matching ?
    regex = '^%s S(\d+)E(\d+) ' % serie['name']
    if serie.get('hd', 0):
        feed = feeds.get('hd',
            ET.parse(urllib.urlopen('http://rss.thepiratebay.se/208')))
        regex += '720p '
    else:
        feed = feeds.get('lo',
            ET.parse(urllib.urlopen('http://rss.thepiratebay.se/205')))
    regex += '(?:HDTV|WEBRip) x264-\w+ \[(?:eztv|PublicHD)\]$'
    regex = regex.replace(' ', '.')
    # Search for new episodes to download
    for item in feed.getroot()[0].findall('item'):
        title = item.find('title').text
        match = re.match(regex, title, re.IGNORECASE)
        if match:
            season, episode = serie['season'], serie['episode']
            download_magnet(item, match, season, episode, serie)


# Download subtitles from addic7ed.com
if SUBTITLES_PATH:
    addic7ed = urllib.urlopen('http://www.addic7ed.com/rss.php?mode=hotspot')
    addic7ed = ET.parse(addic7ed)
    for item in addic7ed.getroot()[0].findall('item'):
        language = item.find('description').text.split(', ')[1]
        if language == 'English':
            title = item.find('title').text
            for serie in SERIES:
                regex = r"^%s - " % serie['name']
                if re.match(regex, title):
                    link = item.find('link').text
                    filename = os.path.join(SUBTITLES_PATH, title+'.srt')
                    urllib.urlretrieve(link, filename)
                    break


if downloads and EMAIL_USER:
    # Save new state
    config = 'SERIES = ' + json.dumps(SERIES, indent=4)
    context = {
        'config': config.replace('\\\\', '\\'),
        'script': os.path.abspath(__file__)
    }
    subprocess.call(
        "CONFIG='%(config)s';"
        "awk -v config=\"$CONFIG\""
        "   '/^# <CONFIG>/{p=1;print;print config;}/# <\/CONFIG>$/{p=0}!p'"
        "   %(script)s > %(script)s.tmp;"
        "mv %(script)s.tmp %(script)s;"
            % context, shell=True)
    
    # Send email
    msg = MIMEMultipart()
    msg['From'] = EMAIL_USER
    msg['To'] = ', '.join(EMAIL_RECIPIENTS)
    msg['Subject'] = "%d New Downloads Available" % len(downloads)
    msg.attach(MIMEText('\n'.join([d[0] for d in downloads])))
    server = smtplib.SMTP(EMAIL_SMTP_HOST, EMAIL_SMTP_PORT)
    server.ehlo()
    server.starttls()
    server.ehlo()
    server.login(EMAIL_USER, EMAIL_PASSWORD)
    server.sendmail(EMAIL_USER, EMAIL_RECIPIENTS, msg.as_string())
    server.close()

    print downloads

