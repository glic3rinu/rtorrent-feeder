import logging
import os
import re
import xml.etree.ElementTree as ET

from . import utils


post_feed = utils.Signal()


class TPBFeeder(object):
    @property
    def feed_domain(self):
        from . import settings
        return getattr(settings, 'TPB_DOMAIN', 'thepiratebay.mn')
    
    def get_regex(self, serie):
        quality = serie.get('quality', 'hd')
        if quality not in ('720p', '1080p'):
            quality = ''
        regex = '^%s (?:20[0-9][0-9] )?S(\d+)E(\d+).+' % serie['name']
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
        domain = self.feed_domain
        try:
            return {
                'hd': ET.parse(utils.fetch_url('https://rss.%s/208' % domain)),
                'lo': ET.parse(utils.fetch_url('https://rss.%s/205' % domain)),
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
                s, e = [ int(n) for n in match.groups()[:2] ]
                if s > 19: # Workaround to some wrongly labeled episodes
                    continue
                if str(s)+str(e) in found:
                    continue
                found.add(str(s)+str(e))
                if self.is_new_episode(serie, s, e):
                    magnet = self.get_magnet(item)
                    yield magnet, s, e
    
    def feed(self):
        from . import settings
        for serie in settings.SERIES:
            max_s = 0
            max_e = 0
            for magnet, s, e in self.find_new_episodes(serie):
                utils.save_as_torrent(magnet)
                max_s = max(max_s, s)
                max_e = max(max_e, e)
                q = ' HD' if serie.get('hd', 0) else ''
                label = "%s S%0.2dE%0.2d%s" % (serie['name'], s, e, q)
                logging.info('Downloaded: %s' % label)
                post_feed.send(type(self), serie, s, e)
                yield label
            if max_s != 0:
                self.update_serie(serie, max_s, max_e)



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
        regex = r'(magnet:\?xt=.*=%s S\d+E\d+[^"]+%s[^"]+)'% (serie['name'], quality)
        regex = regex.replace(' ', '.')
        logging.info('TPBHTML magnet_regex: %s' % regex)
        return regex
    
    def _get_feeds(self):
        domain = self.feed_domain
        try:
            return {
                'hd': utils.fetch_url('https://%s/browse/208/0/9/0' % domain).read(),
                'lo': utils.fetch_url('https://%s/browse/205/0/9/0' % domain).read(),
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
                s, e = [ int(n) for n in match.groups()[:2] ]
                if s > 19: # Workaround to some wrongly labeled episodes
                    continue
                if str(s)+str(e) in found:
                    continue
                found.add(str(s)+str(e))
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
            return ET.parse(utils.fetch_url(feed))
        except IOError, e:
            if getattr(e, 'code', 0) == 404:
                logging.error('Not Found: %s' % feed)
                return ET.ElementTree()
            logging.error('KickAss seems down: %s' % feed)
            raise
    
    def is_trusted(self, item):
        return item.find('{http://xmlns.ezrss.it/0.1/}verified').text == '1'
    
    def get_regex(self, serie):
        regex = '^%s (?:20[0-9][0-9] )?S(\d+)E(\d+).+' % serie['name']
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
            ezrss = utils.fetch_url(url)
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
        name = serie['name'].replace('Mr ', 'Mr. ')
        return '^%s - (\d+)x(\d+) - ' % name
    
    def feed(self):
        from . import settings
        try:
            addic7ed = ET.parse(utils.fetch_url(self.url))
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
                        html = '\n'.join(utils.fetch_url(link).readlines())
                        path = re.findall('(/original/\d+/0)', html)[0]
                        link = 'http://www.addic7ed.com' + path
                        content = utils.fetch_url(
                            link,
                            headers={
                                'Referer': 'http://www.addic7ed.com/'
                            }
                        )
                        with open(filename, 'wb') as subtitle:
                            subtitle.write(content.read())
                        post_feed.send(type(self), serie, s, e, filename)
                        break
        return []
