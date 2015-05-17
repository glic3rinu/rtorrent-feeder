import logging

from . import settings, utils, downloaders


logging.basicConfig(level=settings.LOG_LEVEL or logging.ERROR)


for feeder in settings.FEEDERS:
    feeders.append(utils.import_class(feeder)())


downloads = []
for feeder in feeders:
    try:
        for download in feeder.download():
            downloads.append(download)
    except IOError:
        pass
    except Exception as err:
        logging.error('%s on %s: %s' % (type(err).__name__, type(feeder).__name__, err))


if downloads:
    utils.save_state()
    if settings.EMAIL_USER:
        utils.send_email(downloads)
