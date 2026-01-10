"""Google Drive storage module for M Number folder creation.

Uses a service account to upload files to a shared Google Drive folder.
"""
import json
import os
import logging
from io import BytesIO
from typing import Optional

# Google API imports
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseUpload
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    logging.warning("Google API libraries not installed. Run: pip install google-api-python-client google-auth")


# Scopes for Google Drive API
SCOPES = ['https://www.googleapis.com/auth/drive']

# Cache for the Drive service
_drive_service = None


def _get_credentials():
    """Get credentials from environment variable."""
    creds_json = os.environ.get('GOOGLE_DRIVE_CREDENTIALS')
    if not creds_json:
        raise ValueError("GOOGLE_DRIVE_CREDENTIALS environment variable not set")
    
    creds_dict = json.loads(creds_json)
    return service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)


def _get_drive_service():
    """Get or create the Google Drive service."""
    global _drive_service
    if _drive_service is None:
        credentials = _get_credentials()
        _drive_service = build('drive', 'v3', credentials=credentials)
    return _drive_service


def find_folder_by_name(name: str, parent_id: Optional[str] = None) -> Optional[str]:
    """Find a folder by name, optionally within a parent folder. Supports Shared Drives."""
    service = _get_drive_service()
    
    query = f"name = '{name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    
    # includeItemsFromAllDrives and supportsAllDrives enable Shared Drive support
    results = service.files().list(
        q=query,
        spaces='drive',
        fields='files(id, name)',
        includeItemsFromAllDrives=True,
        supportsAllDrives=True
    ).execute()
    
    files = results.get('files', [])
    return files[0]['id'] if files else None


def create_folder(name: str, parent_id: Optional[str] = None) -> str:
    """Create a folder and return its ID. Supports Shared Drives."""
    service = _get_drive_service()
    
    file_metadata = {
        'name': name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    if parent_id:
        file_metadata['parents'] = [parent_id]
    
    # supportsAllDrives enables Shared Drive support
    folder = service.files().create(
        body=file_metadata, 
        fields='id',
        supportsAllDrives=True
    ).execute()
    return folder['id']


def get_or_create_folder(name: str, parent_id: Optional[str] = None) -> str:
    """Get existing folder or create new one."""
    folder_id = find_folder_by_name(name, parent_id)
    if folder_id:
        return folder_id
    return create_folder(name, parent_id)


def upload_file(file_bytes: bytes, filename: str, folder_id: str, mime_type: str = 'image/jpeg') -> str:
    """Upload a file to a folder and return its ID. Supports Shared Drives."""
    service = _get_drive_service()
    
    file_metadata = {
        'name': filename,
        'parents': [folder_id]
    }
    
    media = MediaIoBaseUpload(BytesIO(file_bytes), mimetype=mime_type, resumable=True)
    
    # supportsAllDrives enables Shared Drive support
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id',
        supportsAllDrives=True
    ).execute()
    
    return file['id']


def create_m_number_folder_simple(
    m_number: str,
    description: str,
    color: str,
    size: str,
    mounting_type: str,
    parent_folder_id: str
) -> dict:
    """
    Create a simple M Number folder with just images subfolder.
    Minimal API calls for speed.
    
    Returns dict with folder IDs.
    """
    # Format display names
    SIZE_DISPLAY = {'dracula': 'Dracula', 'saville': 'Saville', 'dick': 'Dick', 'barzan': 'Barzan', 'baby_jesus': 'Baby_Jesus'}
    COLOR_DISPLAY = {'silver': 'Silver', 'gold': 'Gold', 'white': 'White'}
    
    mounting_display = "Self Adhesive" if mounting_type == "self_adhesive" else "Pre-Drilled"
    color_display = COLOR_DISPLAY.get(color.lower(), color.title())
    size_display = SIZE_DISPLAY.get(size.lower(), size.title())
    
    folder_name = f"{m_number} {mounting_display} {description} aluminium sign {color_display} {size_display}"
    
    # Create main M Number folder
    main_folder_id = get_or_create_folder(folder_name, parent_folder_id)
    
    # Create only images subfolder (minimal API calls)
    folders = {
        'main': main_folder_id,
        '002_images': get_or_create_folder('002 Images', main_folder_id),
    }
    
    return folders


def is_configured() -> bool:
    """Check if Google Drive is configured."""
    if not GOOGLE_API_AVAILABLE:
        return False
    return bool(os.environ.get('GOOGLE_DRIVE_CREDENTIALS'))


def get_parent_folder_id() -> Optional[str]:
    """Get the parent folder ID from environment."""
    return os.environ.get('GOOGLE_DRIVE_PARENT_FOLDER_ID')
