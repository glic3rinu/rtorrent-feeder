import json
import logging
import os
import smtplib
import re
import subprocess
import urllib
import xml.etree.ElementTree as ET
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText


# The following CONFIG block will be used as JSON-based persistent storage
#   'name' should be the exact, case-sensitive, tv show title
#   If 'hd' is set to 0, or not set, only low quality will be downloaded
#   If 'hd' is set to 1 only 720p (HD) episodes will be downloaded
#
# # <CONFIG>
# SERIES = [
#    {
#        "season": 1, 
#        "episode": 10, 
#        "name": "Breaking Bad", 
#        "hd": 1
#    }, 
# ]
# # </CONFIG>
#
# ** DON'T REMOVE <CONFIG> </CONFIG> LABELS **
#
# <CONFIG>
SERIES = []
# </CONFIG>


SUBTITLES_PATH = ''
SUBTITLES_LANGUAGE = 'English'
TORRENT_WATCH_PATH = ''
TPB_TRUSTED_USERS = ['eztv', 'DibyaTPB']
LOG_LEVEL = logging.ERROR

EMAIL_USER = ''
EMAIL_PASSWORD = ''
EMAIL_RECIPIENTS = []
EMAIL_SMTP_HOST = ''
EMAIL_SMTP_PORT = 25


logging.basicConfig(level=LOG_LEVEL or logging.ERROR)


def download_magnet(item, match, season, episode, serie):
    """ Downloads item's magnet if match is a new episode """
    s, e = [ int(e) for e in match.groups() ]
    if s > 19: # Workaround to some wrongly labeled episodes
        return
    if s > season or (s == season and e > episode):
        torrent = '{http://xmlns.ezrss.it/0.1/}torrent'
        magnetURI = '{http://xmlns.ezrss.it/0.1/}magnetURI'
        magnet = item.find(torrent).find(magnetURI).text
        logging.info('Downloading %s' % magnet)
        context = {
            'magnet': magnet,
            'torrent_watch_path': TORRENT_WATCH_PATH
        }
        subprocess.call(
            'MAGNET="%(magnet)s";'
            'cd %(torrent_watch_path)s;'
            '[[ "$MAGNET" =~ xt=urn:btih:([^&/]+) ]] || exit;'
            'echo "d10:magnet-uri${#MAGNET}:${MAGNET}e"'
            '   > "meta-${BASH_REMATCH[1]}.torrent";'
            % context, shell=True, executable='/bin/bash')
        title = item.find('title').text
        downloads.append((title, serie))
        serie['season'] = max(serie['season'], s)
        serie['episode'] = max(serie['episode'], e)


downloads = []


# Download magnets from EZRSS
base_url = 'http://ezrss.it/search/index.php'
for serie in SERIES:
    # Construct URL query
    name = serie['name'].replace(' ', '+')
    if serie.get('hd', 0):
        quality = 'quality=720p'
    else:
        quality = 'quality=HDTV&quality_exact=true'
    query = 'show_name=%s&show_name_exact=true&%s&mode=rss' % (name, quality)
    url = base_url + '?' + query
    try:
        ezrss = urllib.urlopen(url)
    except IOError:
        logging.error('Querying %s ABORTING' % url)
        break
    if ezrss.getcode() != 200:
        logging.error('Querying %s' % url)
        continue
    logging.info('Querying %s' % url)
    # Search for new episodes to download
    ezrss = ET.parse(ezrss)
    regex = '.* Season: (\d+); Episode: (\d+)$'
    season, episode = serie['season'], serie['episode']
    for item in ezrss.getroot()[0].findall('item'):
        description = item.find('description').text
        match = re.match(regex, description)
        download_magnet(item, match, season, episode, serie)


# Download magnets from The Pirate Bay, only from TPB_TRUSTED_USERS
try:
    feeds = {
        'hd': ET.parse(urllib.urlopen('http://rss.thepiratebay.se/208')),
        'lo': ET.parse(urllib.urlopen('http://rss.thepiratebay.se/205'))
    }
except IOError, ET.ParseError:
    logging.error('TPB seems down')
else:
    for serie in SERIES:
        # Construct regular expression and select quality feed
        regex = '^%s S(\d+)E(\d+).+' % serie['name']
        feed = feeds['lo']
        if serie.get('hd', 0):
            feed = feeds['hd']
            regex += '720p '
        regex = regex.replace(' ', '.')
        logging.info('TPB regex: %s' % regex)
        # Search for new episodes to download
        for item in feed.getroot()[0].findall('item'):
            title = item.find('title').text
            match = re.match(regex, title, re.IGNORECASE)
            creator = '{http://purl.org/dc/elements/1.1/}creator'
            if match and item.find(creator).text in TPB_TRUSTED_USERS:
                season, episode = serie['season'], serie['episode']
                download_magnet(item, match, season, episode, serie)


# Download subtitles from addic7ed.com
if SUBTITLES_PATH:
    addic7ed = urllib.urlopen('http://www.addic7ed.com/rss.php?mode=hotspot')
    addic7ed = ET.parse(addic7ed)
    for item in addic7ed.getroot()[0].findall('item'):
        language = item.find('description').text.split(', ')[1]
        if language == SUBTITLES_LANGUAGE:
            title = item.find('title').text
            for serie in SERIES:
                regex = r"^%s - " % serie['name']
                if re.match(regex, title):
                    link = item.find('link').text
                    filename = os.path.join(SUBTITLES_PATH, title+'.srt')
                    urllib.urlretrieve(link, filename)
                    break


if downloads:
    # Save new state
    config = 'SERIES = ' + json.dumps(SERIES, indent=4)
    context = {
        'config': config.replace('\\\\', '\\'),
        'script': os.path.abspath(__file__)
    }
    subprocess.call(
        "CONFIG='%(config)s';"
        "awk -v config=\"$CONFIG\""
        "   '/^# <CONFIG>/{p=1; print; print config;}/# <\/CONFIG>$/{p=0}!p'"
        "   %(script)s > %(script)s.tmp;"
        "mv %(script)s.tmp %(script)s;"
        % context, shell=True)
    
    if EMAIL_USER:
        # Send email
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = ', '.join(EMAIL_RECIPIENTS)
        msg['Subject'] = "%d New Downloads Available" % len(downloads)
        msg.attach(MIMEText('\n'.join([d[0] for d in downloads])))
        logging.info('Sending email to %s' % msg['To'])
        server = smtplib.SMTP(EMAIL_SMTP_HOST, EMAIL_SMTP_PORT)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_USER, EMAIL_RECIPIENTS, msg.as_string())
        server.close()
