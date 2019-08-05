from __future__ import print_function
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from datetime import datetime
import requests
import re
import json

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

spreadsheet_id = '1qeNHHjKFi9b-XZBaQ_zzgxdprKvBiAm1rhXwJrwPokw'

def main():
    creds = None
    
    apikey_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "UploadPrograms\\apikey.json")
    credentials_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "UploadPrograms\\credentials.json")
    token_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "UploadPrograms\\token.pickle")
    
    with open(apikey_path) as api_key:    
        headers = json.load(api_key)
        
    creds = None
    
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path, SCOPES)
            creds = flow.run_local_server()
        # Save the credentials for the next run
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)
    
    service = build('sheets', 'v4', credentials=creds)
    
    # Forms orders.json of orders today
    now = datetime.now()
    url = 'https://api.veeqo.com/orders?created_at_min=%s&page_size=100' % now.strftime("%Y-%m-%d")
    
    try:
        orders = requests.get(url, headers=headers).json() #Veeqo json
        print('<p>Downloaded veeqo json script.</p>')
        
        # Find last row containing data
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range='Sheet1!E:E').execute()

    except:
        print('Error downloading Veeqo/Google Script')
    
    existing_orders = result.get('values', [])
    order_num = re.findall(r'\d+', str(existing_orders))
    
    values = []
    
    for order in orders:
        if (order['channel']['id'] == 55175
            and str(order['id']) not in order_num):
            # items list to store items from order
            items = ''
            i = 0
            for sellable in order['line_items']:
                items += sellable['sellable']['product_title'].upper()       
            
            customer_info = order['deliver_to']
            order_date = re.findall('\d+', str(order['created_at']))

            po_num = ''
            note_nums = re.findall('\d+', str(order['customer_note']['text']))
            if note_nums:
                for num in note_nums:
                    if len(num) == 9:
                        po_num = num
                    
            # Creates values list for spreadsheet input data
            try:
                values.append (
                    [order['total_price'],
                    '','',
                    po_num,
                    order['number'],
                    order_date[2]+'/'+order_date[1]+'/'+order_date[0],
                    '','',
                    customer_info['first_name'].upper(),
                    customer_info['last_name'].upper(),
                    customer_info['address1'].upper(),
                    customer_info['zip'].upper(),
                    '','',
                    items,
                    '',
                    order['subtotal_price']
                    ])
            except:
                print('Error appending values')
                
            if order['status'] == 'cancelled':
                print('<p>Cancelled order ' + order['number'] + ' not uploaded</p>')
                del values[-1]
            
            else:
                print('<p>Order ' + order['number']+ ' uploaded.</p>')

    
    if values:
        # Appending to sheets
        body = {
            'values': values
        }
    
        range_str = 'Sheet1!A'+str(len(existing_orders) + 1)+':V'
        value_input_option = 'RAW'
        
        try:
            result = service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_str, # Append order to next row 
                valueInputOption=value_input_option,
                body=body).execute()

        except:
            print('Error uploading to sheets')
        
    else:
        print('<p>No orders uploaded :(</p>')

if __name__ == '__main__':
    main()

