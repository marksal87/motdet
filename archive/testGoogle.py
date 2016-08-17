# Copied from:
# https://developers.google.com/api-client-library/python/start/get_started

import httplib2
import sys

from apiclient.discovery import build
from oauth2client import tools
from oauth2client.file import Storage
from oauth2client.client import AccessTokenRefreshError
from oauth2client.client import OAuth2WebServerFlow

import os.path
from googleapiclient.http import MediaFileUpload

# For this example, the client id and client secret are command-line arguments.
client_id = '1063090033010-t20sinv44p6ricj27kcspt2si444ffng.apps.googleusercontent.com'
client_secret = 'OwQwlGyT_CfVMNtZLqJWxNwu'

# The scope URL for read/write access to a user's calendar data
#scope = 'https://www.googleapis.com/auth/calendar'
scope = 'https://www.googleapis.com/auth/drive'

# Create a flow object. This object holds the client_id, client_secret, and
# scope. It assists with OAuth 2.0 steps to get user authorization and
# credentials.
flow = OAuth2WebServerFlow(client_id, client_secret, scope)

def main():

  # Create a Storage object. This object holds the credentials that your
  # application needs to authorize access to the user's data. The name of the
  # credentials file is provided. If the file does not exist, it is
  # created. This object can only hold credentials for a single user, so
  # as-written, this script can only handle a single user.
  storage = Storage('credentials.dat')

  # The get() function returns the credentials for the Storage object. If no
  # credentials were found, None is returned.
  credentials = storage.get()

  # If no credentials are found or the credentials are invalid due to
  # expiration, new credentials need to be obtained from the authorization
  # server. The oauth2client.tools.run_flow() function attempts to open an
  # authorization server page in your default web browser. The server
  # asks the user to grant your application access to the user's data.
  # If the user grants access, the run_flow() function returns new credentials.
  # The new credentials are also stored in the supplied Storage object,
  # which updates the credentials.dat file.
  if credentials is None or credentials.invalid:
    credentials = tools.run_flow(flow, storage, tools.argparser.parse_args())

  # Create an httplib2.Http object to handle our HTTP requests, and authorize it
  # using the credentials.authorize() function.
  http = httplib2.Http()
  http = credentials.authorize(http)

  # The apiclient.discovery.build() function returns an instance of an API service
  # object can be used to make API calls. The object is constructed with
  # methods specific to the calendar API. The arguments provided are:
  #   name of the API ('calendar')
  #   version of the API you are using ('v3')
  #   authorized httplib2.Http() object that can be used for API calls
  #service = build('calendar', 'v3', http=http)
  service = build('drive', 'v3', http=http)

  try:
    #parentFolderID = "0B9M2ehh0drEDdUtSRnJtbjBWUE0"
    folder_id = "0B9M2ehh0drEDdUtSRnJtbjBWUE0"
    snapshot_file_path = "/home/pi/faces/tstupload.jpg"
    file_name = os.path.basename(snapshot_file_path)
    print(file_name)
    media = MediaFileUpload(snapshot_file_path, mimetype='image/jpeg')
    fileNameTestVariable = "dog.jpg"
    fileBody2 = {
        #'name': 'TstUploadMark.jpg',
        'name': fileNameTestVariable,
        'description': 'test description',
        'mimeType': 'image/jpeg',
        'parents': [
            "0B9M2ehh0drEDdUtSRnJtbjBWUE0"
         ]
    }
    print(fileBody2)
    request = service.files().create(body=fileBody2, media_body=media)
    response = request.execute()
    print("\nResponse:")
    print(response)

    # The Calendar API's events().list method returns paginated results, so we
    # have to execute the request in a paging loop. First, build the
    # request object. The arguments provided are:
    #   primary calendar for user
#    request = service.files().list(pageSize=4)
    # Loop until all pages have been processed.
#    while request != None:
      # Get the next page.
#      response = request.execute()
      # Accessing the response like a dict object with an 'items' key
      # returns a list of item objects (events).
#      for ifile in response.get('files', []):
        # The ifile object is a dict object with a 'summary' key.
#        print(repr(ifile.get('name', 'NO NAME')) + '\n')
      # Get the next request object by passing the previous request object to
      # the list_next method.
#      request = service.files().list_next(request, response)
#      request = None

  except AccessTokenRefreshError:
    # The AccessTokenRefreshError exception is raised if the credentials
    # have been revoked by the user or they have expired.
    print ('The credentials have been revoked or expired, please re-run'
           'the application to re-authorize')

if __name__ == '__main__':
  main()
