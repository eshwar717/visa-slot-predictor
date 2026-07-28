import os.path
import re
import base64
import time
import pandas as pd
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_gmail_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)

def get_email_body(payload):
    body_data = ""
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] in ['text/plain', 'text/html']:
                data = part.get('body', {}).get('data', '')
                if data:
                    body_data += base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
            elif 'parts' in part:
                body_data += get_email_body(part)
    else:
        data = payload.get('body', {}).get('data', '')
        if data:
            body_data = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
    return body_data

def extract_target_months(body_text):
    pattern = r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(202[6-9])'
    matches = re.findall(pattern, body_text, re.IGNORECASE)
    if not matches:
        return "Unknown"
    unique_months = list(set([f"{m[0].capitalize()} {m[1]}" for m in matches]))
    unique_months.sort(key=lambda d: datetime.strptime(d, "%B %Y"))
    return ", ".join(unique_months)

def parse_subject_details(df):
    if df.empty or 'subject' not in df.columns:
        return df
    df['visa_type'] = [re.search(r'\d+\s+([A-Z0-9/]+\([A-Za-z]+\))', str(s)).group(1) if re.search(r'\d+\s+([A-Z0-9/]+\([A-Za-z]+\))', str(s)) else "Unknown" for s in df['subject']]
    df['vac_location'] = [re.search(r'-([A-Z\s]+VAC)', str(s)).group(1).strip() if re.search(r'-([A-Z\s]+VAC)', str(s)) else "Unknown" for s in df['subject']]
    df['target_city'] = [re.search(r'\|\s*([A-Z\s]+)\s+slot-dates', str(s)).group(1).strip() if re.search(r'\|\s*([A-Z\s]+)\s+slot-dates', str(s)) else "Unknown" for s in df['subject']]
    return df

def get_email_images(service, msg_id, payload):
    image_paths = []
    if not os.path.exists("screenshots"):
        os.makedirs("screenshots")
        
    def walk_parts(part):
        if part.get('mimeType', '').startswith('image/'):
            attachment_id = part.get('body', {}).get('attachmentId')
            if attachment_id:
                attachment = service.users().messages().attachments().get(
                    userId='me', messageId=msg_id, id=attachment_id
                ).execute()
                data = attachment.get('data')
                if data:
                    img_data = base64.urlsafe_b64decode(data)
                    filename = part.get('filename') or "screenshot.png"
                    filepath = os.path.join("screenshots", f"{msg_id}_{filename}")
                    with open(filepath, "wb") as f:
                        f.write(img_data)
                    image_paths.append(filepath)
                    
        if 'parts' in part:
            for subpart in part['parts']:
                walk_parts(subpart)
                
    walk_parts(payload)
    return ", ".join(image_paths)

def sync_data():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Syncing latest visa slots from Gmail...")
    service = get_gmail_service()
    query = "in:anywhere from:alerts@checkvisaslots.com"
    
    results = service.users().messages().list(userId='me', q=query, maxResults=100).execute()
    messages = results.get('messages', [])
    
    if not messages:
        print("No emails found.")
        return

    email_data = []
    for msg in messages:
        try:
            response = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
            payload = response.get('payload', {})
            headers = payload.get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
            timestamp = datetime.fromtimestamp(int(response.get('internalDate', 0)) / 1000.0)
            
            body_text = get_email_body(payload)
            slot_match = re.search(r'Minimum Available Slots:\s*(\d+)', body_text, re.IGNORECASE)
            
            screenshot_paths = get_email_images(service, msg['id'], payload)
            
            email_data.append({
                'id': response['id'], 'subject': subject, 
                'available_slots': int(slot_match.group(1)) if slot_match else 1,
                'target_months': extract_target_months(body_text),
                'timestamp': timestamp, 'day_of_week': timestamp.strftime('%A'),
                'hour': timestamp.hour, 'date': timestamp.strftime('%Y-%m-%d'),
                'screenshots': screenshot_paths
            })
        except Exception as e:
            continue

    df = pd.DataFrame(email_data)
    if not df.empty:
        df = df.sort_values(by='timestamp', ascending=False).reset_index(drop=True)
        df = parse_subject_details(df)
        df.to_csv("visa_alerts_history.csv", index=False)
        print(f"Successfully saved {len(df)} records to CSV.")

while True:
    sync_data()
    print("Waiting 5 minutes before the next check...")
    time.sleep(300)
