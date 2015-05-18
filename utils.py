import json
import logging
import os
import smtplib
import subprocess
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText


def save_state():
    from . import settings
    state = 'SERIES = ' + json.dumps(settings.SERIES, indent=4)
    context = {
        'state': state.replace('\\\\', '\\'),
        'script': os.path.join(os.path.dirname(os.path.abspath(__file__)), 'settings.py')
    }
    subprocess.call(
        "STATE='%(state)s';"
        "awk -v state=\"$STATE\""
        "   '/^# <STATE>/{p=1; print; print state;}/# <\/STATE>$/{p=0}!p'"
        "   %(script)s > %(script)s.tmp;"
        "mv %(script)s.tmp %(script)s;"
        % context, shell=True)


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
