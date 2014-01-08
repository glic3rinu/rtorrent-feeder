import json
import logging
import os
import smtplib
import re
import subprocess
import urllib2
import xml.etree.ElementTree as ET
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText


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
SERIES = []
# </STATE>

SUBTITLES_PATH = '' # Leave blank if you don't want subtitles to be downloaded
SUBTITLES_LANGUAGE = 'English'
TORRENT_WATCH_PATH = ''
TPB_TRUSTED_USERS = ['eztv', 'DibyaTPB']
LOG_LEVEL = logging.ERROR

EMAIL_USER = '' # Leave blank if you don't want email alerts
EMAIL_PASSWORD = ''
EMAIL_RECIPIENTS = []
EMAIL_SMTP_HOST = ''
EMAIL_SMTP_PORT = 25


logging.basicConfig(level=LOG_LEVEL or logging.ERROR)

downloads = []


def download_magnet(item):
    """ Downloads item's magnet """
    torrent = '{http://xmlns.ezrss.it/0.1/}torrent'
    magnetURI = '{http://xmlns.ezrss.it/0.1/}magnetURI'
    magnet = item.find(torrent).find(magnetURI).text
    logging.info('Downloading %s' % magnet)
    context = {
        'magnet': magnet,
        'torrent_watch_path': TORRENT_WATCH_PATH
    }
    # Convert magnet to torrent file
    subprocess.call(
        'MAGNET="%(magnet)s";'
        'cd %(torrent_watch_path)s;'
        '[[ "$MAGNET" =~ xt=urn:btih:([^&/]+) ]] || exit;'
        'echo "d10:magnet-uri${#MAGNET}:${MAGNET}e"'
        '   > "meta-${BASH_REMATCH[1]}.torrent";'
        % context, shell=True, executable='/bin/bash')
    title = item.find('title').text
    downloads.append(title)


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
        ezrss = urllib2.urlopen(url)
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
        s, e = [ int(e) for e in match.groups() ]
        if s > 19: # Workaround to some wrongly labeled episodes
            continue
        if s > season or (s == season and e > episode):
            download_magnet(item)
            serie['season'] = max(serie['season'], s)
            serie['episode'] = max(serie['episode'], e)


# Download magnets from The Pirate Bay, only from TPB_TRUSTED_USERS
try:
    feeds = {
        'hd': ET.parse(urllib2.urlopen('http://rss.thepiratebay.se/208')),
        'lo': ET.parse(urllib2.urlopen('http://rss.thepiratebay.se/205'))
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
        season, episode = serie['season'], serie['episode']
        for item in feed.getroot()[0].findall('item'):
            title = item.find('title').text
            match = re.match(regex, title, re.IGNORECASE)
            creator = '{http://purl.org/dc/elements/1.1/}creator'
            creator = item.find(creator).text
            if match and (not TPB_TRUSTED_USERS or creator in TPB_TRUSTED_USERS):
                s, e = [ int(e) for e in match.groups() ]
                if s > season or (s == season and e > episode):
                    download_magnet(item)
                    serie['season'] = max(serie['season'], s)
                    serie['episode'] = max(serie['episode'], e)


# Download subtitles from addic7ed.com
# This will probably only work consistently with English language
if SUBTITLES_PATH:
    addic7ed = urllib2.urlopen('http://www.addic7ed.com/rss.php?mode=hotspot')
    addic7ed = ET.parse(addic7ed)
    for item in addic7ed.getroot()[0].findall('item'):
        language = item.find('description').text.split(', ')[-1]
        if language == SUBTITLES_LANGUAGE:
            title = item.find('title').text
            for serie in SERIES:
                regex = r"^%s - " % serie['name']
                if re.match(regex, title, re.IGNORECASE):
                    filename = os.path.join(SUBTITLES_PATH, title+'.srt')
                    # Anonymous users are limited to 15 downloads, don't waste them
                    if not os.path.exists(filename):
                        link = item.find('link').text
                        html = '\n'.join(urllib2.urlopen(link).readlines())
                        path = re.findall('(/original/\d+/0)', html)[0]
                        link = 'http://www.addic7ed.com' + path
                        request = urllib2.Request(link)
                        # Fake a browser request
                        request.add_header('Referer', 'http://www.addic7ed.com/')
                        response = urllib2.urlopen(request)
                        with open(filename, 'wb') as subtitle:
                            subtitle.write(response.read())
                        break

if downloads:
    # Save new state
    state = 'SERIES = ' + json.dumps(SERIES, indent=4)
    context = {
        'state': state.replace('\\\\', '\\'),
        'script': os.path.abspath(__file__)
    }
    subprocess.call(
        "STATE='%(state)s';"
        "awk -v state=\"STATE\""
        "   '/^# <STATE>/{p=1; print; print state;}/# <\/STATE>$/{p=0}!p'"
        "   %(script)s > %(script)s.tmp;"
        "mv %(script)s.tmp %(script)s;"
        % context, shell=True)
    
    if EMAIL_USER:
        # Send email
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = ', '.join(EMAIL_RECIPIENTS)
        msg['Subject'] = "%d New Downloads Available" % len(downloads)
        if len(downloads) == 1:
            msg['Subject'] = "One New Download Available"
        msg.attach(MIMEText('\n'.join(downloads)))
        logging.info('Sending email to %s' % msg['To'])
        server = smtplib.SMTP(EMAIL_SMTP_HOST, EMAIL_SMTP_PORT)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_USER, EMAIL_RECIPIENTS, msg.as_string())
        server.close()
