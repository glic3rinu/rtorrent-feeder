import ast
import gzip
import json
import logging
import os
import smtplib
import subprocess
import urllib2
from StringIO import StringIO

from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText


def get_settings_path():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(current_dir, 'settings.py')
    return path


def get_series_lineno(settings_path):
    with open(settings_path, 'rb') as handler:
        p = ast.parse(handler.read())
    found = False
    for elem in p.body:
        targets = getattr(elem, 'targets', None)
        if targets:
            if found:
                return found, elem.lineno-1
            var_name = targets[0].id
            if var_name == 'SERIES':
                found = elem.lineno


def fetch_url(url, headers=None, timeout=5):
    extra_headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept-encoding': 'gzip'
    }
    extra_headers.update(headers or {})
    request = urllib2.Request(url, headers=extra_headers)
    response = urllib2.urlopen(request, timeout=timeout)
    if response.info().get('Content-Encoding') == 'gzip':
        buf = StringIO(response.read())
        f = gzip.GzipFile(fileobj=buf)
        f.getcode = lambda f: response.getcode()
        return f
    else:
        return response


def apply_changes(settings_path, ini, end):
    from . import settings
    content = []
    inside = False
    with open(settings_path, 'r') as handler:
        for num, line in enumerate(handler.readlines(), 1):
            line = line.rstrip()
            if num == ini:
                inside = True
                series = settings.SERIES
                content.append(
                    'SERIES = %s' % json.dumps(series, indent=4)
                )
            elif num == end:
                inside = False
                content.append('')
            elif not inside:
                content.append(line)
    return '\n'.join(content)


def save_series(backup=True):
    settings_path = get_settings_path()
    ini, end = get_series_lineno(settings_path)
    content = apply_changes(settings_path, ini, end)
    tmp_settings_path = settings_path + '.tmp'
    with open(tmp_settings_path, 'w') as handle:
        handle.write(content)
    if backup:
        os.rename(settings_path, settings_path + '.backup')
    os.rename(tmp_settings_path, settings_path)


def send_email(downloads):
    from . import settings
    msg = MIMEMultipart()
    msg['From'] = settings.EMAIL_USER
    msg['To'] = ', '.join(settings.EMAIL_RECIPIENTS)
    if len(downloads) == 1:
        msg['Subject'] = "One New Download Available"
    else:
        msg['Subject'] = "%d New Downloads Available" % len(downloads)
    msg.attach(MIMEText('\n'.join(downloads)))
    logging.info('Sending email to %s' % msg['To'])
    server = smtplib.SMTP(settings.EMAIL_SMTP_HOST, settings.EMAIL_SMTP_PORT)
    server.ehlo()
    server.starttls()
    server.ehlo()
    server.login(settings.EMAIL_USER, settings.EMAIL_PASSWORD)
    server.sendmail(settings.EMAIL_USER, settings.EMAIL_RECIPIENTS, msg.as_string())
    server.close()


def save_as_torrent(magnet):
    from . import settings
    context = {
        'magnet': magnet,
        'torrent_watch_path': settings.TORRENT_WATCH_PATH
    }
    # Convert magnet to torrent file
    subprocess.call(
        'MAGNET="%(magnet)s";'
        'cd %(torrent_watch_path)s;'
        '[[ "$MAGNET" =~ xt=urn:btih:([^&/]+) ]] || exit;'
        'echo "d10:magnet-uri${#MAGNET}:${MAGNET}e"'
        '   > "meta-${BASH_REMATCH[1]}.torrent";'
        % context, shell=True, executable='/bin/bash')


class Signal(object):
    _registry = {}
    
    def connect(self, func, senders=None):
        if senders is None:
            senders = [None]
        for sender in senders:
            try:
                self._registry[sender].append(func)
            except KeyError:
                self._registry[sender] = [func]
    
    def send(self, sender, *args, **kwargs):
        for func in self._registry.get(sender, []) + self._registry.get(None, []):
            func(sender, *args, **kwargs)


def standardize(filename, serie, s, e):
    extension = filename[-3:]
    name = serie['name'].replace(' ', '.')
    name += '.S%02dE%02d.' % (s, e)
    name += extension
    return name


def import_class(cls):
    module = '.'.join(cls.split('.')[:-1])
    cls = cls.split('.')[-1]
    module = __import__(module, fromlist=[module])
    return getattr(module, cls)
