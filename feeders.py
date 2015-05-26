import logging
import os
import re
import urllib2
import xml.etree.ElementTree as ET

from . import utils


post_feed = utils.Signal()


class TPBFeeder(object):
    def get_regex(self, serie):
        quality = serie.get('quality', 'hd')
        if quality not in ('720p', '1080p'):
            quality = ''
        regex = '^%s S(\d+)E(\d+).+' % serie['name']
        regex = regex.replace(' ', '.')
        logging.info('TPB regex: %s' % regex)
        return regex
    
    def get_feed(self, serie):
        self._cached_feeds = getattr(self, '_cached_feeds', None) or self._get_feeds()
        quality = serie.get('quality')
        if quality in ('hd', '1080p', '720p'):
            return self._cached_feeds['hd']
        return self._cached_feeds['lo']
    
    def _get_feeds(self):
        try:
            return {
                'hd': ET.parse(urllib2.urlopen('http://rss.thepiratebay.se/208')),
                'lo': ET.parse(urllib2.urlopen('http://rss.thepiratebay.se/205'))
            }
        except:
            logging.error('TPB seems down')
            raise IOError
    
    def is_trusted(self, item):
        from . import settings
        user = self.get_user(item)
        return bool(not settings.TPB_TRUSTED_USERS or user in settings.TPB_TRUSTED_USERS)
    
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
        found = set()
        try:
            root = feed.getroot()[0]
        except (IndexError, TypeError):
            return
        for item in root.findall('item'):
            title = self.get_title(item)
            match = re.match(regex, title, re.IGNORECASE)
            if match and self.is_trusted(item):
                s, e = [ int(e) for e in match.groups()[:2] ]
                if s > 19: # Workaround to some wrongly labeled episodes
                    continue
                if s+e in found:
                    continue
                found.add(s+e)
                if self.is_new_episode(serie, s, e):
                    magnet = self.get_magnet(item)
                    yield magnet, s, e
    
    def feed(self):
        from . import settings
        for serie in settings.SERIES:
            for magnet, s, e in self.find_new_episodes(serie):
                utils.save_as_torrent(magnet)
                self.update_serie(serie, s, e)
                q = ' HD' if serie.get('hd', 0) else ''
                label = "%s S%0.2dE%0.2d%s" % (serie['name'], s, e, q)
                logging.info('Downloaded: %s' % label)
                post_feed.send(type(self), serie, s, e)
                yield label


class TPBHTMLFeeder(TPBFeeder):
    def get_regex(self, serie):
        regex = r'magnet:\?xt=.*=%s S(\d+)E(\d+).+' % serie['name']
        regex = regex.replace(' ', '.')
        logging.info('TPBHTML regex: %s' % regex)
        return regex
    
    def get_magnet_regex(self, serie):
        quality = serie.get('quality', 'hd')
        if quality not in ('720p', '1080p'):
            quality = ''
        regex = r'(magnet:\?xt=.*=%s S\d+E\d+.+%s[^"]+)'% (serie['name'], quality)
        regex = regex.replace(' ', '.')
        logging.info('TPBHTML magnet_regex: %s' % regex)
        return regex
    
    def _get_feeds(self):
        headers = {
            'User-Agent': 'Mozilla/5.0',
        }
        hq_req = urllib2.Request('https://thepiratebay.se/browse/208/0/9/0', headers=headers)
        lo_req = urllib2.Request('https://thepiratebay.se/browse/205/0/9/0', headers=headers)
        try:
            return {
                'hd': urllib2.urlopen(hq_req).read(),
                'lo': urllib2.urlopen(lo_req).read()
            }
        except:
            logging.error('TPB seems down')
            raise
    
    def is_trusted(self, magnet, feed):
        from . import settings
        feed = feed.replace('\n', ' ')
        td = re.findall(r'<td>.*(<a href="%s".*?)</td>' % re.escape(magnet), feed)[0]
        user = re.findall(r'<a href="/user/(.*?)">', td)[0]
        return bool(' alt="VIP" ' in td or (not settings.TPB_TRUSTED_USERS or user in settings.TPB_TRUSTED_USERS))
    
    def find_new_episodes(self, serie):
        feed = self.get_feed(serie)
        magnet_regex = self.get_magnet_regex(serie)
        found = set()
        for magnet in re.findall(magnet_regex, feed, re.IGNORECASE):
            if self.is_trusted(magnet, feed):
                regex = self.get_regex(serie)
                match = re.match(regex, magnet, re.IGNORECASE)
                s, e = [ int(e) for e in match.groups()[:2] ]
                if s > 19: # Workaround to some wrongly labeled episodes
                    continue
                if s+e in found:
                    continue
                found.add(s+e)
                if self.is_new_episode(serie, s, e):
                    yield magnet, s, e


class KickAssFeeder(TPBFeeder):
    base_url = 'https://kat.cr/usearch/category%3Atv%20{name}%20{quality}/?rss=1'
    
    def get_feed(self, serie):
        name = '%20'.join(serie['name'].split())
        quality = serie.get('quality', 'hd')
        if quality == 'hd':
            quality = '1080p%20OR%20720p'
        elif quality not in ('1080p', '720p'):
            quality = '-1080p%20-720p'
        feed = self.base_url.format(name=name, quality=quality)
        logging.info('KICKASS feed: %s' % feed)
        try:
            return ET.parse(urllib2.urlopen(feed, timeout=10))
        except IOError, e:
            if getattr(e, 'code', 0) == 404:
                logging.error('Not Found: %s' % feed)
                return ET.ElementTree()
            logging.error('KickAss seems down: %s' % feed)
            raise
    
    def is_trusted(self, item):
        return item.find('author') is not None
    
    def get_regex(self, serie):
        regex = '^%s S(\d+)E(\d+).+' % serie['name']
        regex = regex.replace(' ', '.')
        logging.info('KICKASS regex: %s' % regex)
        return regex


class EZRSSFeeder(TPBFeeder):
    base_url = 'http://ezrss.it/search/index.php'
    
    def is_trusted(self, item):
        return True
    
    def get_feed(self, serie):
        name = serie['name'].replace(' ', '+')
        quality = serie.get('quality', 'hd')
        if quality in ('720p', '1080p'):
            quality = 'quality=' + quality
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
    
    def get_regex(self, serie):
        return '^%s - (\d+)x(\d+) - ' % serie['name']
    
    def feed(self):
        from . import settings
        try:
            addic7ed = ET.parse(urllib2.urlopen(self.url))
        except:
            raise IOError
        for item in addic7ed.getroot()[0].findall('item'):
            language = item.find('description').text.split(', ')[-1]
            if language == settings.SUBTITLES_LANGUAGE:
                title = item.find('title').text
                filename = os.path.join(settings.SUBTITLES_PATH, title+'.srt')
                for serie in settings.SERIES:
                    regex = self.get_regex(serie)
                    match = re.match(regex, title, re.IGNORECASE)
                    if match and not os.path.exists(filename):
                        s, e = [ int(e) for e in match.groups() ]
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
                        post_feed.send(type(self), serie, s, e, filename)
                        break
        return []