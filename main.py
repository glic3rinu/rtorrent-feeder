import logging
import traceback
import urllib2

from . import settings, utils

logging.basicConfig(level=settings.LOG_LEVEL or logging.ERROR)

try:
    # Custo signals
    from . import signals
except ImportError:
    logging.info("Custom signals not installed.")
    pass


feeders = []
for feeder in settings.FEEDERS:
    feeders.append(utils.import_class(feeder)())


downloads = []
for feeder in feeders:
    try:
        for feed in feeder.feed():
            downloads.append(feed)
    except (IOError, urllib2.URLError, urllib2.HTTPError) as err:
        logging.error('%s on %s: %s' % (type(err).__name__, type(feeder).__name__, err))
    except Exception as err:
        logging.error('%s on %s: %s' % (type(err).__name__, type(feeder).__name__, err))
        logging.error(traceback.format_exc())


if downloads:
    utils.save_series()
    if settings.EMAIL_USER:
        utils.send_email(downloads)
