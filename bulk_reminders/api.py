from __future__ import print_function

import datetime
import os.path
import re
import traceback
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
SCOPES = ['https://www.googleapis.com/auth/calendar']
TIME_REGEX = re.compile(r'\d{2}:\d{2}(?:AM|PM)')
DATE_FORMAT = '%Y-%m-%d'
DATETIME_FORMAT = DATE_FORMAT + ' %H:%M%p'


class Calendar(object):
    def __init__(self) -> None:
        self.credentials: Optional[Credentials] = None
        self.service: Optional[Resource] = None

    def save_token(self) -> None:
        """Store the credentials for later use."""
        with open('token.json', 'w') as token:
            token.write(self.credentials.to_json())

    def authenticate_via_token(self) -> bool:
        """Attempt to login using the tokens stored in token.json"""
        if os.path.exists('token.json'):
            self.credentials = Credentials.from_authorized_user_file('token.json', SCOPES)
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                try:
                    self.credentials.refresh(Request())
                except BaseException as e:
                    traceback.print_exc()
                    return False
                self.save_token()
            return True
        return False

    def authenticate_via_oauth(self) -> bool:
        """Attempt to acquire credentials"""
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
            self.credentials = flow.run_local_server(port=0)
            self.save_token()
        except BaseException as e:
            traceback.print_exc()
            return False

    def setupService(self) -> None:
        """Setup the Google App Engine API Service for the Calendar API"""
        self.service = build('calendar', 'v3', credentials=self.credentials)

    def getCalendars(self) -> Iterator[Any]:
        """Retrieve all calendar data"""
        page_token = None
        while True:
            calendar_list = self.service.calendarList().list(pageToken=page_token, minAccessRole='writer').execute()
            for entry in calendar_list['items']:
                # Referencing the primary calendar should be done with the ID 'primary'
                if entry.get('primary', False):
                    entry['id'] = 'primary'

                yield entry

            # Continue loading more calendars
            page_token = calendar_list.get('nextPageToken')
            if page_token is None:
                break

    def getEvents(self, calendarID: str) -> List[Any]:
        """Retrieves up to 2500 events for a given calendar ordered by occurrence that happen in the future."""
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
                 description: Optional[str] = None):
        if type(start) != type(end):
            raise Exception("Both start and end times need to be either simple dates or advanced datetime objects.")
        self.summary, self.start, self.end, self.description = summary, start, end, description

    @classmethod
    def from_api(cls, event: dict) -> 'Event':
        """Returns a Event object from a Google API Engine item."""
        print(event)
        return Event(summary=event.get('summary'),
                     start=isoparse(event['start'].get('dateTime', event['start'].get('date'))),
                     end=isoparse(event['end'].get('dateTime', event['end'].get('date'))),
                     description=event.get('description'))

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
            return {'datetime': self.start.astimezone(get_localzone()).isoformat()}

    @property
    def api_end(self) -> dict:
        """Provides a proper object for the 'end' field in the body of a new event."""
        if type(self.end) is datetime.date:
            return {'date': self.end.strftime('%Y-%m-%d')}
        elif type(self.end) is datetime.datetime:
            return {'datetime': self.end.astimezone(get_localzone()).isoformat()}

    def fill_row(self, row: int, table: QTableWidget) -> None:
        """Fills a specific row on a QTableWidget object with the information stored in the Event object."""
        summaryItem = QTableWidgetItem(self.summary)
        summaryItem.setForeground(QtGui.QColor("blue"))
        table.setItem(row, 0, summaryItem)

        formatString = '%b %d, %Y' if self.start is not None else '%b %d, %Y %I:%M %Z'
        table.setItem(row, 1, QTableWidgetItem('Foreign'))
        table.setItem(row, 2, QTableWidgetItem(self.start.strftime(formatString)))
        table.setItem(row, 3, QTableWidgetItem(self.end.strftime(formatString)))

    @classmethod
    def parse_raw(self, input: Tuple[str]) -> 'Event':
        """Takes in input that has been separated by a RegEx expression into groups and creates a Event object"""
        first_time = re.match(TIME_REGEX, input[2]) is not None
        second_time = re.match(TIME_REGEX, input[3 + (1 if first_time else 0)])
        second_index = 2 + (1 if first_time else 0)  # Shortcut
        # Yeah this logic is really scuffed, but I really don't have a better way right now
        start = datetime.datetime.strptime(DATETIME_FORMAT if first_time else DATE_FORMAT,
                                           input[1] + (input[second_index - 1] if first_time else ''))
        end = datetime.datetime.strptime(DATETIME_FORMAT if second_time else DATE_FORMAT,
                                         input[second_index] + (input[second_index + 1] if second_time else ''))
        return Event(
                summary=input[0],
                start=start,
                end=end
        )
