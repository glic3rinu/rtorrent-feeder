import logging

from . import settings, utils, downloaders


logging.basicConfig(level=settings.LOG_LEVEL or logging.ERROR)


feeders = [
    downloaders.KickAssDownloader(),
    downloaders.TPBDownloader(),
    downloaders.EZRSSDownloader(),
]


if settings.SUBTITLES_PATH:
    feeders.append(downloaders.Addic7edDownloader())


downloads = []
for feeder in feeders:
    try:
        downloads += feeder.download()
    except IOError:
        pass


if downloads:
    utils.save_state()
    if settings.EMAIL_USER:
        utils.send_email()

