import logging
import traceback

from . import settings, utils, downloaders


logging.basicConfig(level=settings.LOG_LEVEL or logging.ERROR)


feeders = []
for feeder in settings.FEEDERS:
    feeders.append(feeder())


downloads = []
for feeder in feeders:
    try:
        for download in feeder.download():
            downloads.append(download)
    except IOError as err:
        logging.error('%s on %s: %s' % (type(err).__name__, type(feeder).__name__, err))
    except Exception as err:
        logging.error('%s on %s: %s' % (type(err).__name__, type(feeder).__name__, err))
        logging.error(traceback.format_exc())


if downloads:
    utils.save_state()
    if settings.EMAIL_USER:
        utils.send_email(downloads)
