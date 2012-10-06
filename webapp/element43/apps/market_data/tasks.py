# Utility imports
import datetime
import pytz
from celery.task.schedules import crontab
from celery.task import PeriodicTask, Task
from celery import Celery
import ast
from django.db import connection

# Models
from apps.market_data.models import History, OrderHistory

class ProcessHistory(PeriodicTask):
    
    """
    Post-process history table
    """
    
    run_every = datetime.timedelta(hours=24)
    
    def run(self, **kwargs):
        print "BEGIN HISTORY PROCESSING"
        regions = History.objects.order_by('mapregion').distinct('mapregion')
        for region in regions.iterator():
            ProcessRegionHistory.delay(region.mapregion)
    
class ProcessRegionHistory(Task):
    
    def run(self, region):
        print "History processing for region: ", region
        utc = pytz.UTC
        history = History.objects.filter(mapregion_id = region)
        for message in history.iterator():
            data = ast.literal_eval(message.history_data)
            for k,v in data.iteritems():
                date = utc.localize(datetime.datetime.strptime(k, "%Y-%m-%d %H:%M:%S"))
                if OrderHistory.objects.filter(date = date, invtype = message.invtype).count() == 0:
                    new_history = OrderHistory(mapregion=message.mapregion,
                                               invtype=message.invtype,
                                               date = date,
                                               numorders=v[0],
                                               low=v[1],
                                               high=v[2],
                                               mean=v[3],
                                               quantity=v[4])
                    try:
                        new_history.save()
                    except:
                        print "ERROR: ", connection.queries
                else:
                    pass
        print "Completed: ", region