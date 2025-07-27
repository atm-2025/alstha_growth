import os
import json
import pickle
import subprocess
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, 
    QComboBox, QCheckBox, QFileDialog, QMessageBox
)

# Constants
UPLOAD_JSON_DIR = os.path.join(os.path.dirname(__file__), "../upload-json")
os.makedirs(UPLOAD_JSON_DIR, exist_ok=True)

class UploadYTGTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.yt_dir, self.g_dir = self.ensure_dirs()
        self.status = QTextEdit()
        self.status.setReadOnly(True)
        # YouTube account selection
        from PySide6.QtWidgets import QComboBox
        self.yt_account_box = QComboBox()
        self.yt_account_box.setToolTip("Select YouTube account")
        self.yt_account_box.addItem("(Choose or add account)")
        self.yt_account_map = self.load_yt_accounts()  # {email: client_secret_filename}
        self.yt_account_emails = list(self.yt_account_map.keys())
        for email in self.yt_account_emails:
            self.yt_account_box.addItem(email)
        layout.addWidget(QLabel("YouTube Account:"))
        layout.addWidget(self.yt_account_box)
        # Google Drive account selection
        self.account_box = QComboBox()
        self.account_box.setToolTip("Select Google Drive account")
        self.account_box.addItem("(Choose or add account)")
        self.account_map = self.load_known_accounts()  # {email: client_secret_filename}
        self.account_emails = list(self.account_map.keys())
        for email in self.account_emails:
            self.account_box.addItem(email)
        layout.addWidget(QLabel("Google Drive Account:"))
        layout.addWidget(self.account_box)
        checkbox_style = """
        QCheckBox::indicator {
            width: 24px;
            height: 24px;
        }
        QCheckBox::indicator:unchecked {
            border: 2px solid #0078d7;
            background: #fff;
        }
        QCheckBox::indicator:checked {
            border: 2px solid #0078d7;
            background: #0078d7;
        }
        QCheckBox::indicator:pressed {
            background: #000;
            border: 2px solid #0078d7;
        }
        """
        # YouTube files with checkboxes
        self.yt_files = self.get_files(self.yt_dir)
        from PySide6.QtWidgets import QCheckBox, QHBoxLayout
        layout.addWidget(QLabel("YouTube Files:"))
        self.yt_checkboxes = []
        for fname in self.yt_files:
            row = QHBoxLayout()
            cb = QCheckBox(fname)
            cb.setStyleSheet(checkbox_style)
            row.addWidget(cb)
            layout.addLayout(row)
            self.yt_checkboxes.append((cb, fname))
        self.yt_upload_btn = QPushButton("Upload to YouTube")
        self.yt_upload_btn.clicked.connect(self.upload_yt)
        layout.addWidget(self.yt_upload_btn)
        # Google Drive files with checkboxes
        self.g_files = self.get_files(self.g_dir)
        layout.addWidget(QLabel("Google Drive Files:"))
        self.g_checkboxes = []
        for fname in self.g_files:
            row = QHBoxLayout()
            cb = QCheckBox(fname)
            cb.setStyleSheet(checkbox_style)
            row.addWidget(cb)
            layout.addLayout(row)
            self.g_checkboxes.append((cb, fname))
        self.g_upload_btn = QPushButton("Upload to Google Drive")
        self.g_upload_btn.clicked.connect(self.upload_g)
        layout.addWidget(self.g_upload_btn)
        layout.addWidget(QLabel("Status:"))
        layout.addWidget(self.status)
        self.setLayout(layout)

    def load_yt_accounts(self):
        import json
        acc_path = os.path.join(UPLOAD_JSON_DIR, 'yt_accounts.json')
        if os.path.exists(acc_path):
            with open(acc_path, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return {email: '' for email in data}
                return data
        return {}

    def save_yt_accounts(self, accounts):
        import json
        acc_path = os.path.join(UPLOAD_JSON_DIR, 'yt_accounts.json')
        with open(acc_path, 'w') as f:
            json.dump(accounts, f)

    def ensure_dirs(self):
        # Point to the correct directory structure
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
        base = os.path.join(project_root, 'web_app', 'files', 'uploading_yt_G')
        yt = os.path.join(base, 'yt')
        g = os.path.join(base, 'google')
        os.makedirs(yt, exist_ok=True)
        os.makedirs(g, exist_ok=True)
        return yt, g

    def get_files(self, folder):
        return [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]

    def load_known_accounts(self):
        import json
        acc_path = os.path.join(UPLOAD_JSON_DIR, 'gdrive_accounts.json')
        if os.path.exists(acc_path):
            with open(acc_path, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return {email: '' for email in data}
                return data
        return {}

    def save_known_accounts(self, accounts):
        import json
        acc_path = os.path.join(UPLOAD_JSON_DIR, 'gdrive_accounts.json')
        with open(acc_path, 'w') as f:
            json.dump(accounts, f)

    def upload_yt(self):
        selected_files = [fname for cb, fname in self.yt_checkboxes if cb.isChecked()]
        if not selected_files:
            self.status.append("No files selected for YouTube upload.")
            return
        idx = self.yt_account_box.currentIndex()
        if idx <= 0 or idx > len(self.yt_account_emails):
            from PySide6.QtWidgets import QFileDialog
            self.status.append("No YouTube account selected, please choose your client_secret JSON file...")
            secrets_path, _ = QFileDialog.getOpenFileName(self, "Select YouTube client_secret JSON", UPLOAD_JSON_DIR, "JSON Files (*.json)")
            if not secrets_path:
                self.status.append("No client_secret file selected. Aborting.")
                return
            try:
                import pickle
                from google_auth_oauthlib.flow import InstalledAppFlow
                from googleapiclient.discovery import build as build2
                from google.auth.transport.requests import Request
                import json
                SCOPES = [
                    'openid',
                    'https://www.googleapis.com/auth/youtube.upload',
                    'https://www.googleapis.com/auth/userinfo.email'
                ]
                flow = InstalledAppFlow.from_client_secrets_file(secrets_path, SCOPES)
                creds = flow.run_local_server(port=0)
                service2 = build2('oauth2', 'v2', credentials=creds)
                user_info = service2.userinfo().get().execute()
                actual_email = user_info['email']
                cred_path2 = os.path.join(UPLOAD_JSON_DIR, f'token_yt_{actual_email}.pickle')
                with open(cred_path2, 'wb') as token:
                    pickle.dump(creds, token)
                # Save mapping
                self.yt_account_map[actual_email] = os.path.basename(secrets_path)
                self.save_yt_accounts(self.yt_account_map)
                if actual_email not in self.yt_account_emails:
                    self.yt_account_emails.append(actual_email)
                    self.yt_account_box.addItem(actual_email)
                self.yt_account_box.setCurrentIndex(self.yt_account_emails.index(actual_email)+1)
                email = actual_email
                secrets_path = os.path.join(UPLOAD_JSON_DIR, self.yt_account_map[email])
            except Exception as e:
                self.status.append(f"❌ YouTube login failed: {e}")
                self.status.append("Please select a YouTube account.")
                return
        else:
            email = self.yt_account_emails[idx-1]
            secrets_path = os.path.join(UPLOAD_JSON_DIR, self.yt_account_map[email])
        self.status.append(f"Uploading {len(selected_files)} files to YouTube as {email}...")
        try:
            import pickle
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload
            from google.auth.transport.requests import Request
            import json
            SCOPES = [
                'openid',
                'https://www.googleapis.com/auth/youtube.upload',
                'https://www.googleapis.com/auth/userinfo.email'
            ]
            creds = None
            cred_path = os.path.join(UPLOAD_JSON_DIR, f'token_yt_{email}.pickle')
            if os.path.exists(cred_path):
                with open(cred_path, 'rb') as token:
                    creds = pickle.load(token)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(secrets_path, SCOPES)
                    creds = flow.run_local_server(port=0)
                    from googleapiclient.discovery import build as build2
                    service2 = build2('oauth2', 'v2', credentials=creds)
                    user_info = service2.userinfo().get().execute()
                    actual_email = user_info['email']
                    cred_path2 = os.path.join(UPLOAD_JSON_DIR, f'token_yt_{actual_email}.pickle')
                    with open(cred_path2, 'wb') as token:
                        pickle.dump(creds, token)
                    if actual_email not in self.yt_account_emails:
                        self.yt_account_emails.append(actual_email)
                        self.yt_account_map[actual_email] = os.path.basename(secrets_path)
                        self.save_yt_accounts(self.yt_account_map)
                        self.yt_account_box.addItem(actual_email)
                    email = actual_email
            service = build('youtube', 'v3', credentials=creds)
            for fname in selected_files:
                fpath = os.path.join(self.yt_dir, fname)
                body = {
                    'snippet': {
                        'title': fname,
                        'description': 'Uploaded by alstha_growth app',
                        'tags': ['alstha_growth'],
                        'categoryId': '22'  # People & Blogs
                    },
                    'status': {
                        'privacyStatus': 'private'
                    }
                }
                media = MediaFileUpload(fpath, resumable=True)
                request = service.videos().insert(part=','.join(body.keys()), body=body, media_body=media)
                response = request.execute()
                self.status.append(f"✅ Uploaded to YouTube: {fname} (ID: {response['id']})")
        except Exception as e:
            self.status.append(f"❌ YouTube upload failed: {e}")

    def upload_g(self):
        selected_files = [fname for cb, fname in self.g_checkboxes if cb.isChecked()]
        if not selected_files:
            self.status.append("No files selected for Google Drive upload.")
            return
        idx = self.account_box.currentIndex()
        if idx <= 0 or idx > len(self.account_emails):
            from PySide6.QtWidgets import QFileDialog
            self.status.append("No Google Drive account selected, please choose your client_secret JSON file...")
            secrets_path, _ = QFileDialog.getOpenFileName(self, "Select Google Drive client_secret JSON", UPLOAD_JSON_DIR, "JSON Files (*.json)")
            if not secrets_path:
                self.status.append("No client_secret file selected. Aborting.")
                return
            try:
                import pickle
                from google_auth_oauthlib.flow import InstalledAppFlow
                from googleapiclient.discovery import build as build2
                from google.auth.transport.requests import Request
                import json
                SCOPES = [
                    'openid',
                    'https://www.googleapis.com/auth/drive.file',
                    'https://www.googleapis.com/auth/userinfo.email'
                ]
                flow = InstalledAppFlow.from_client_secrets_file(secrets_path, SCOPES)
                creds = flow.run_local_server(port=0)
                service2 = build2('oauth2', 'v2', credentials=creds)
                user_info = service2.userinfo().get().execute()
                actual_email = user_info['email']
                cred_path2 = os.path.join(UPLOAD_JSON_DIR, f'token_gdrive_{actual_email}.pickle')
                with open(cred_path2, 'wb') as token:
                    pickle.dump(creds, token)
                # Save mapping
                self.account_map[actual_email] = os.path.basename(secrets_path)
                self.save_known_accounts(self.account_map)
                if actual_email not in self.account_emails:
                    self.account_emails.append(actual_email)
                    self.account_box.addItem(actual_email)
                self.account_box.setCurrentIndex(self.account_emails.index(actual_email)+1)
                email = actual_email
                secrets_path = os.path.join(UPLOAD_JSON_DIR, self.account_map[email])
            except Exception as e:
                self.status.append(f"❌ Google Drive login failed: {e}")
                self.status.append("Please select a Google Drive account.")
                return
        else:
            email = self.account_emails[idx-1]
            secrets_path = os.path.join(UPLOAD_JSON_DIR, self.account_map[email])
        self.status.append(f"Uploading {len(selected_files)} files to Google Drive as {email}...")
        try:
            import pickle
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload
            from google.auth.transport.requests import Request
            import json
            SCOPES = [
                'openid',
                'https://www.googleapis.com/auth/drive.file',
                'https://www.googleapis.com/auth/userinfo.email'
            ]
            creds = None
            cred_path = os.path.join(UPLOAD_JSON_DIR, f'token_gdrive_{email}.pickle')
            if os.path.exists(cred_path):
                with open(cred_path, 'rb') as token:
                    creds = pickle.load(token)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(secrets_path, SCOPES)
                    creds = flow.run_local_server(port=0)
                    from googleapiclient.discovery import build as build2
                    service2 = build2('oauth2', 'v2', credentials=creds)
                    user_info = service2.userinfo().get().execute()
                    actual_email = user_info['email']
                    cred_path2 = os.path.join(UPLOAD_JSON_DIR, f'token_gdrive_{actual_email}.pickle')
                    with open(cred_path2, 'wb') as token:
                        pickle.dump(creds, token)
                    if actual_email not in self.account_emails:
                        self.account_emails.append(actual_email)
                        self.account_map[actual_email] = os.path.basename(secrets_path)
                        self.save_known_accounts(self.account_map)
                        self.account_box.addItem(actual_email)
                    email = actual_email
            service = build('drive', 'v3', credentials=creds)
            for fname in selected_files:
                fpath = os.path.join(self.g_dir, fname)
                file_metadata = {'name': fname}
                media = MediaFileUpload(fpath, resumable=True)
                file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
                self.status.append(f"✅ Uploaded to Google Drive: {fname} (ID: {file.get('id')})")
        except Exception as e:
            self.status.append(f"❌ Google Drive upload failed: {e}") 