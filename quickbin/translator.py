#!/usr/bin/env python
# script to translate text calendar events into ics format
import sys

from icalendar import Calendar, Event, vDatetime
#from datetime import datetime
#from datetime import date
import datetime


#
#today = datetime.now()

#
schedule_dir = '/Users/maezono/Dropbox/01backup/01Documents/01Leaved/04Memorandum/'
ical_dir =''
filename = '01scheduleGIP_autogen'

PUBLIC_HEADING = '    '
PRIVATE_HEADING = '        '
KUGIRI = '%%%%%%%%%%%%%%%%%%'

#
def derive_stat(event):
    stat_tuple = (0,0,0,0)
    return stat_tuple

def parse_labfor(string):
    """Return icalendar event from sche events"""

        today = datetime.date.today()

def generate_format(calendar):
    """Return lab-formatted calendar schedule string from ics file"""
    class extending_cal:
        def __init__(self):
            pass
        def stringify(self, tag, heading):
            return heading + self.decoded(heading).decode("utf-8").strip()
    #print(cal)
    for component in cal.walk():
        # only takes events
        if component.name == 'VEVENT':
            # instantiate extended object
            event = extending_cal(component)
            #print(component.get_inline('description'))
            print(component.decoded('dtstart'))
            #print(datetime.date.fromtimestamp(component.decoded('dtstart')))
            #print(datetime.date.today())
            print(component.decoded('dtend'))
            #print(component.decoded('summary')) # this will become the 4-spaced part
            summary = component.stringify(PUBLIC_HEADING, 'summary')
            print(summary)
            #print(component.decoded('location'))
            description = PRIVATE_HEADING + component.decoded('description').decode("utf-8").strip()
            print(component.decoded('description'))
            ##except AttributeError:
            #print('element {} has incomplete attribute'.format(component.name))
            #print(component.location)
            print('--------------------------------')
        #print(component.name)
        #print(component)
    return string

if __name__ == "__main__":
    print(datetime.datetime.now())
    work_ics = sys.argv[1]#'test.ics'
    with open (work_ics, 'rb') as ics:
        cal = Calendar.from_ical(ics.read())
        #print (vDatetime.from_ical(ics.read))
        generate_format(cal)
