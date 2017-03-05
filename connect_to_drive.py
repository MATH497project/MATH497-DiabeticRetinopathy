from __future__ import print_function
import os
import io
try:
    import httplib2
    from apiclient import discovery
    from oauth2client import client
    from oauth2client import tools
    from oauth2client.file import Storage

    from apiclient import errors
    from apiclient import http
except:
    print('Run the following code to install the module: \n \
    pip install --upgrade google-api-python-client')

# The following codes and instances are used for the first time authorizing the
# connection and getting the credentials. Put the drive-python-quickstart.json in
# the same folder as the codes and use it instead.
"""
# If modifying these scopes, delete your previously saved credentials
# at ~/drive-python-quickstart.json
try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None
SCOPES = 'https://www.googleapis.com/auth/drive'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Drive API Python Quickstart'"""

def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    """credential_dir = os.getcwd()
    credential_path = os.path.join(credential_dir,
                                   'drive-python-quickstart.json')
    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials"""
    store = Storage('drive-python-quickstart.json')
    credentials = store.get()
    return credentials

def get_file_id(service, file_name):
    """Search the drive and find the file id of the given file name.

    Args:
      service: Drive API service instance.
      file_name: Name of the file to search.

    Returns:
      The exclusive id of the file. If there are multiple files with the same name.
      return None and pritn error.
    """
    results = service.files().list().execute()
    items_raw = results.get('items', [])
    items = [item for item in items_raw if item.get('title')==file_name]
    if not items:
        print('\tAn error occurred: No files found.')
        return None
    elif len(items)>1:
        print('\tAn error occurred: Duplicated file names! Please check.')
        return None
    else:
        print('\tGot the file id. Print metadata:')
        return items[0].get('id')

def print_file_metadata(service, file_id):
  """Print a file's metadata.

  Args:
    service: Drive API service instance.
    file_id: ID of the file to print metadata for.
  """
  try:
    file = service.files().get(fileId=file_id).execute()

    print ('\t\tTitle: %s' % file['title'])
    print ('\t\tMIME type: %s' % file['mimeType'])
  except errors.HttpError, error:
    print ('\t\tAn error occurred: %s' % error)

def download_file(service, file_id, local_fd):
    """Download a Drive file's content to the local filesystem.

    Args:
    service: Drive API Service instance.
    file_id: ID of the Drive file that will downloaded.
    local_fd: io.Base or file object, the stream that the Drive file's
        contents will be written to.
    """
    request = service.files().get_media(fileId=file_id)
    fh=io.FileIO(local_fd, 'wb')
    media_request = http.MediaIoBaseDownload(fh, request)

    while True:
        try:
            download_progress, done = media_request.next_chunk()
        except errors.HttpError, error:
            print ('\tAn error occurred: %s' % error)
            return
        if download_progress:
            print ('\tDownload Progress: %d%%' % int(download_progress.progress() * 100))
        if done:
            print ('\tDownload Complete')
            return

def check_and_update(table_file_name_dict, local_fd=None):
    """Check if the file exist in the (given) data folder path. If not, connect
    to the drive and download the correct version.

    Args:
      table_file_name_dict: A dict of table name and its corresponding file name.
      local_fd: Give a path to hold the files. If None, the default path will be
    used.

    Returns:
      The path being used.
    """
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('drive', 'v2', http=http)

    print('Local data read/write folder path:')
    if not local_fd:
        local_fd=os.getcwd()+'/data/'
        print('\tDefault path: '+local_fd)
    else:
        print('\tCustomed path: '+local_fd)
    if not os.path.exists(local_fd):
        print('\tCreating the folder...')
        os.makedirs(local_fd)


    for table_name, file_name in table_file_name_dict.items():
        print('\nData: '+table_name+' \nFile: '+file_name)
        if not os.path.exists(local_fd+file_name):
            print('File does not exist. Searching from drive...')
            file_id=get_file_id(service, file_name)
            if file_id:
                print_file_metadata(service,file_id)
                download_file(service, file_id, local_fd+file_name)
        else:
            print('File already exists.')

    return local_fd
