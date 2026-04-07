from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import imaplib
import email
from email.header import decode_header

app = FastAPI(title="Email Parser API")

class EmailCredentials(BaseModel):
    email: str
    password: str
    provider: str  # "gmail" or "outlook"

class EmailStats(BaseModel):
    unread_count: int
    attachment_count: int
    provider: str

def get_imap_server(provider: str) -> str:
    """Get IMAP server based on provider"""
    servers = {
        "gmail": "imap.gmail.com",
        "outlook": "imap-mail.outlook.com"
    }
    return servers.get(provider.lower(), "imap.gmail.com")

@app.post("/email-stats")
async def get_email_stats(credentials: EmailCredentials):
    """Get email statistics: unread count and attachment count"""
    try:
        provider = credentials.provider.lower()
        if provider not in ["gmail", "outlook"]:
            raise HTTPException(status_code=400, detail="Provider must be 'gmail' or 'outlook'")
        
        imap_server = get_imap_server(provider)
        
        # Connect to IMAP server
        mail = imaplib.IMAP4_SSL(imap_server, 993)
        mail.login(credentials.email, credentials.password)
        mail.select("INBOX")
        
        # Get unread count
        status, unread_response = mail.status("INBOX", "(UNSEEN)")
        unread_str = unread_response[0]
        if isinstance(unread_str, bytes):
            unread_str = unread_str.decode('utf-8')
        unread_count = int(unread_str.split()[-1].rstrip(')'))
        
        # Get attachment count
        status, messages = mail.search(None, "ALL")
        message_ids = messages[0].split() if messages[0] else []
        attachment_count = 0
        
        for msg_id in message_ids:
            status, msg_data = mail.fetch(msg_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg_bytes = response_part[1]
                    if isinstance(msg_bytes, str):
                        msg_bytes = msg_bytes.encode('utf-8')
                    msg = email.message_from_bytes(msg_bytes)
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_disposition() == "attachment":
                                attachment_count += 1
                                break
        
        mail.close()
        mail.logout()
        
        return EmailStats(
            unread_count=unread_count,
            attachment_count=attachment_count,
            provider=provider
        )
    
    except imaplib.IMAP4.error as e:
        raise HTTPException(status_code=401, detail=f"IMAP Error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)