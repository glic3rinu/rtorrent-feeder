import logging
import os
import re
import urllib2
import xml.etree.ElementTree as ET

from . import settings, utils


class TPBDownloader(object):
    def get_regex(self, serie):
        regex = '^%s S(\d+)E(\d+).+' % serie['name']
        feed = feeds['lo']
        if serie.get('hd', 0):
            regex += '720p '
        regex = regex.replace(' ', '.')
        logging.info('TPB regex: %s' % regex)
        return regex
    
    def get_feed(self, serie):
        self._cached_feeds = getattr(self, '_cached_feeds', None) or self._get_feeds()
        if serie.get('hd', 0):
            return self._cached_feeds['hd']
        return self._cached_feeds['lo']
    
    def _get_feeds(self):
        try:
            return {
                'hd': ET.parse(urllib2.urlopen('http://rss.thepiratebay.se/208')),
                'lo': ET.parse(urllib2.urlopen('http://rss.thepiratebay.se/205'))
            }
        except IOError, ET.ParseError:
            logging.error('TPB seems down')
            raise IOError
    
    def is_trusted(self, item):
        user = self.get_user(item)
        return bool(not self.TPB_TRUSTED_USERS or user in self.TPB_TRUSTED_USERS)
    
    def get_magnet(self, item):
        magnetURI = '{http://xmlns.ezrss.it/0.1/}magnetURI'
        magnet = item.find(magnetURI)
        return magnet.text
    
    def get_title(self, item):
        return item.find('title').text
    
    def get_user(self, item):
        creator = '{http://purl.org/dc/elements/1.1/}creator'
        return item.find(creator).text
    
    def update_serie(self, serie, s, e):
        serie['season'] = max(serie['season'], s)
        serie['episode'] = max(serie['episode'], e)
    
    def is_new_episode(self, serie, s, e):
        return s > serie['season'] or (s == serie['season'] and e > serie['episode'])
    
    def find_new_episodes(self, serie):
        feed = self.get_feed(serie)
        regex = self.get_regex(serie)
        try:
            root = feed.getroot()[0]
        except IndexError:
            return
        for item in root.findall('item'):
            title = self.get_title(item)
            match = re.match(regex, title, re.IGNORECASE)
            if match and self.is_trusted(item):
                s, e = [ int(e) for e in match.groups() ]
                if s > 19: # Workaround to some wrongly labeled episodes
                    continue
                if self.is_new_episode(serie, s, e):
                    magnet = self.get_magnet(item)
                    yield magnet, s, e
    
    def download(self):
        downloads = []
        for serie in settings.SERIES:
            for magnet, s, e in self.find_new_episodes(serie):
                utils.save_as_torrent(magnet)
                self.update_serie(serie, s, e)
                label = "%s S%iE%i" % (serie['name'], s, e)
                logging.info('Downloaded: %s' % label)
                downloads.append(label)
        return downloads


class KickAssDownloader(TPBDownloader):
    def get_feed(self, serie):
        self._cached_feed = getattr(self, '_cached_feed', None) or self._get_feed()
        return self._cached_feed
    
    def _get_feed(self):
        feed = 'https://kickass.so/usearch/720p%20category%3Atv/?rss=1'
        try:
            return ET.parse(urllib2.urlopen(feed))
        except IOError, ET.ParseError:
            logging.error('TPB seems down')
            raise IOError
    
    def is_trusted(self, item):
        return item.find('author') is not None
    
    def get_regex(self, serie):
        regex = '^%s S(\d+)E(\d+).+' % serie['name']
        regex = regex.replace(' ', '.')
        logging.info('KICKASS regex: %s' % regex)
        return regex


class EZRSSDownloader(TPBDownloader):
    base_url = 'http://ezrss.it/search/index.php'
    
    def is_trusted(self, item):
        return True
    
    def get_feed(self, serie):
        name = serie['name'].replace(' ', '+')
        if serie.get('hd', 0):
            quality = 'quality=720p'
        else:
            quality = 'quality=HDTV&quality_exact=true'
        query = 'show_name=%s&show_name_exact=true&%s&mode=rss' % (name, quality)
        url = self.base_url + '?' + query
        try:
            ezrss = urllib2.urlopen(url)
        except IOError, e:
            logging.error('Querying %s ABORTING' % url)
            raise e
        if ezrss.getcode() != 200:
            logging.error('Querying %s' % url)
            raise IOError
        logging.info('Querying %s' % url)
        return ET.parse(ezrss)
    
    def get_regex(self, serie):
        return '.* Season: (\d+); Episode: (\d+)$'
    
    def get_title(self, item):
        title = item.find('description')
        if title:
            return title.text


class Addic7edDownloader(object):
    url = 'http://www.addic7ed.com/rss.php?mode=hotspot'
    
    def download(self):
        try:
            addic7ed = ET.parse(urllib2.urlopen(self.url))
        except IOError, ET.ParseError:
            raise IOError
        for item in addic7ed.getroot()[0].findall('item'):
            language = item.find('description').text.split(', ')[-1]
            if language == settings.SUBTITLES_LANGUAGE:
                title = item.find('title').text
                filename = os.path.join(settings.SUBTITLES_PATH, title+'.srt')
                for serie in settings.SERIES:
                    regex = r"^%s - " % serie['name']
                    match = re.match(regex, title, re.IGNORECASE) 
                    if match and not os.path.exists(filename):
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
        return []
