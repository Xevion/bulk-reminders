# bulk-reminders

Do you use Google Calendars to track your classes? I do. Or at least I'm trying to.

The issue with this is that the way of setting up all the times is quick annoying, and I would like to do it all in one go without lifting a finger for the most part.

This is a very small app designed to do that exactly.

For example, a simple input like such:

```
08/23 08/29 "Module 1
```

## Features

- Small GUI for interacting with the Google Calendar API
- Bulk Text to API/GUI translation
- Easy undo button

## API Setup

This application uses a testing API and is not built for production usage. Just a warning before you try and set this up.

1. [Create a Google API Project and enable the Calendar API](https://developers.google.com/calendar/api/quickstart/python)

2. [Add a user as a test user](https://i.imgur.com/wKp0ipd.png)

3. Create OAuth2.0 Credentials and download the file. Rename it and place it in the root of the repository directory.

4. Start the application. Follow the prompt and sign in with the test user you added.
