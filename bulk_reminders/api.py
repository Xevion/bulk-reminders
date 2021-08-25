from __future__ import print_function

import datetime
import os.path
import traceback
from typing import Any, Iterator, List, Optional, Tuple

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar']


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

    def getEvents(self, calendarID: str) -> None:
        now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        events_result = self.service.events().list(calendarId=calendarID, timeMin=now,
                                                   maxResults=10, singleEvents=True,
                                                   orderBy='startTime').execute()
        events = events_result.get('items', [])

    def getCalendarsSimplified(self) -> List[Tuple[str, str]]:
        """Extracts the bare minimum required information from the Calendar."""
        return [(calendar['id'], calendar['summary']) for calendar in self.getCalendars()]


class Event():
    def __init__(self, title, date, time):
        pass
