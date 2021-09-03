from __future__ import print_function

import datetime
import logging
import os.path
import re
from typing import Any, Iterator, List, Optional, Tuple, Union

from PyQt5 import QtGui
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem
from dateutil.parser import isoparse
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build
from tzlocal import get_localzone

# If modifying these scopes, delete the file token.json.
from bulk_reminders import undo

SCOPES = ['https://www.googleapis.com/auth/calendar']
TIME_REGEX = re.compile(r'\d{2}:\d{2}(?:AM|PM)')
DATE_FORMAT = '%Y-%m-%d'
DATETIME_FORMAT = DATE_FORMAT + '%H:%M%p'

logger = logging.getLogger(__file__)
logger.setLevel(logging.DEBUG)


class Calendar(object):
    TOKEN_FILE = 'token.json'

    def __init__(self) -> None:
        self.credentials: Optional[Credentials] = None
        self.service: Optional[Resource] = None

    def save_token(self) -> None:
        """Store the credentials for later use."""
        logger.debug('Saving token to token.json')
        with open(Calendar.TOKEN_FILE, 'w') as token:
            token.write(self.credentials.to_json())

    def authenticate_via_token(self) -> bool:
        """Attempt to login using the tokens stored in token.json"""
        logger.info('Attempting to authenticate via token')
        if os.path.exists(Calendar.TOKEN_FILE):
            self.credentials = Credentials.from_authorized_user_file('token.json', SCOPES)
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                try:
                    logger.info('Refreshing token')
                    self.credentials.refresh(Request())
                except BaseException as e:
                    logger.error('Failed to refresh token', exc_info=e)
                    return False
                else:
                    logger.info('Successfully authenticated via token')
                    self.save_token()
            return True
        return False

    def authenticate_via_oauth(self) -> bool:
        """Attempt to acquire credentials"""
        try:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            self.credentials = flow.run_local_server(port=0)
        except BaseException as e:
            logger.error('Failed to authenticate via OAuth 2.0 flow', exc_info=e)
            return False
        else:
            self.save_token()
            return True

    def setupService(self) -> None:
        """Setup the Google App Engine API Service for the Calendar API"""
        logger.debug('Initializing Calendar API Service')
        self.service = build('calendar', 'v3', credentials=self.credentials)

    def getCalendars(self) -> Iterator[Any]:
        """Retrieve all calendar data"""
        logger.debug('Retrieving all calendar data')
        page, page_token = 1, None
        while True:
            calendar_list = self.service.calendarList().list(pageToken=page_token, minAccessRole='writer').execute()
            for entry in calendar_list['items']:
                # Referencing the primary calendar should be done with the ID 'primary'
                if entry.get('primary', False):
                    entry['id'] = 'primary'

                yield entry

            # Continue loading more calendars
            page += 1
            page_token = calendar_list.get('nextPageToken')
            if page_token is None:
                break

            logger.debug(f'Retrieving page {page} of Calendars')

    def getEvents(self, calendarID: str) -> List[Any]:
        """Retrieves up to 2500 events for a given calendar ordered by occurrence that happen in the future."""
        logger.debug(f'Retrieving all events from Calendar {calendarID}')
        now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        events = self.service.events().list(calendarId=calendarID, timeMin=now,
                                            maxResults=2500, singleEvents=True,
                                            orderBy='startTime').execute()
        return events.get('items', [])

    def getCalendarsSimplified(self) -> List[Tuple[str, str]]:
        """Extracts the bare minimum required information from the Calendar."""
        return [(calendar['id'], calendar['summary']) for calendar in self.getCalendars()]


class Event(object):
    def __init__(self, summary: str, start: Union[datetime.date, datetime.datetime], end: Union[datetime.date, datetime.datetime],
                 description: Optional[str] = None, status: Optional[str] = None):
        if type(start) != type(end):
            raise Exception("Both start and end times need to be either simple dates or advanced datetime objects.")
        self.summary, self.start, self.end, self.description, self.status = summary, start, end, description, status

    @classmethod
    def from_api(cls, event: dict, history: Optional[undo.HistoryManager]) -> 'Event':
        """Returns a Event object from a Google API Engine item."""
        undo_stage = history.exists(event.get('id')) if history is not None else -1
        return Event(summary=event.get('summary'),
                     start=isoparse(event['start'].get('dateTime', event['start'].get('date'))),
                     end=isoparse(event['end'].get('dateTime', event['end'].get('date'))),
                     description=event.get('description'),
                     status=f'Stage {undo_stage}' if undo_stage != -1 else 'Foreign')

    @property
    def body(self) -> dict:
        return {
            'summary': self.summary,
            'description': self.description,
            'start': self.api_start,
            'end': self.api_end
        }

    @property
    def is_datetime(self) -> bool:
        """Returns true if the Event object is based on full datetime objects instead of simple date objects."""
        return type(self.start) is datetime.datetime

    @property
    def api_start(self) -> dict:
        """Provides a proper object for the 'start' field in the body of a new event."""
        if type(self.start) is datetime.date:
            return {'date': self.start.strftime('%Y-%m-%d')}
        elif type(self.start) is datetime.datetime:
            return {'dateTime': self.start.astimezone(get_localzone()).isoformat()}

    @property
    def api_end(self) -> dict:
        """Provides a proper object for the 'end' field in the body of a new event."""
        if type(self.end) is datetime.date:
            return {'date': self.end.strftime('%Y-%m-%d')}
        elif type(self.end) is datetime.datetime:
            return {'dateTime': self.end.astimezone(get_localzone()).isoformat()}

    def fill_row(self, row: int, table: QTableWidget) -> None:
        """Fills a specific row on a QTableWidget object with the information stored in the Event object."""
        summaryItem = QTableWidgetItem(self.summary)
        summaryItem.setForeground(QtGui.QColor("blue"))
        table.setItem(row, 0, summaryItem)

        formatString = '%b %d, %Y' if self.start is not None else '%b %d, %Y %I:%M %Z'
        table.setItem(row, 1, QTableWidgetItem(self.status))
        table.setItem(row, 2, QTableWidgetItem(self.start.strftime(formatString)))
        table.setItem(row, 3, QTableWidgetItem(self.end.strftime(formatString)))

    @classmethod
    def parse_raw(cls, input: Tuple[str]) -> 'Event':
        """Takes in input that has been separated by a RegEx expression into groups and creates a Event object"""
        first_time = input[2] is not None
        start = datetime.datetime.strptime(input[1] + (input[2] if first_time else ''), DATETIME_FORMAT if first_time else DATE_FORMAT)
        if input[3] is not None:
            second_time = input[4] is not None
            end = datetime.datetime.strptime(input[3] + (input[4] if second_time else ''), DATETIME_FORMAT if second_time else DATE_FORMAT)
        else:
            if first_time:
                # But if a start time (hour & minute) was specified, make it end at the same time
                end = start
            else:
                # If no second date is specified and no first time is either, it simply ends the next day and lasts 24 hours
                end = start + datetime.timedelta(hours=24)

        return Event(
                summary=input[0],
                start=start,
                end=end,
                status='Ready'
        )
