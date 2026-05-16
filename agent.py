import os
import asyncio
import base64
import fitz  # PyMuPDF for rendering images
from openai import OpenAI
import markdown
from weasyprint import HTML
import os
from dotenv import load_dotenv

# This tells Python to load the hidden variables from your .env file
load_dotenv()

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient

# Google API Imports
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Instead of pasting the token here, Python will grab it securely from the .env file!
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def extract_text_from_pdf(pdf_bytes):
    """Attempts standard text extraction. If the PDF is a scanned image, falls back to High-Res Vision OCR."""
    text_output = ""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        vision_client = OpenAI(
            base_url="https://models.inference.ai.azure.com",
            api_key=GITHUB_TOKEN
        )
        
        for page_num, page in enumerate(doc):
            page_text = page.get_text().strip()
            
            # If the page has almost no text layer, it's a scan.
            if len(page_text) > 50:
                text_output += page_text + "\n"
            else:
                print(f"   👀 Scanned PDF page detected. Activating High-Res Vision OCR...")
                
                # UPGRADE: Increased DPI to 300 for crystal clear number reading
                pix = page.get_pixmap(dpi=300)
                img_b64 = base64.b64encode(pix.tobytes("png")).decode("utf-8")
                
                # UPGRADE: Stricter prompt explicitly asking for the numbers
                response = vision_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "This is a scanned receipt or invoice. Read the image carefully. Transcribe the vendor name, the line items, and explicitly state the FINAL TOTAL AMOUNT DUE. Ensure numbers are exact."},
                                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
                            ]
                        }
                    ]
                )
                text_output += response.choices[0].message.content + "\n"
                
        return text_output
    except Exception as e:
        return f"[Error parsing PDF content: {str(e)}]"
    
def get_all_unread_invoices():
    """Authenticates with Gmail, fetches emails, and extracts text/images."""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=8080)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('gmail', 'v1', credentials=creds)
    
    print("📬 Scanning inbox for unread bills and invoices...")
    results = service.users().messages().list(userId='me', q='is:unread (invoice OR bill OR statement)', maxResults=5).execute()
    messages = results.get('messages', [])

    if not messages:
        print("❌ No unread financial emails found.")
        return []

    valid_invoices = []

    for m in messages:
        msg = service.users().messages().get(userId='me', id=m['id'], format='full').execute()
        payload = msg.get('payload', {})
        headers = payload.get('headers', [])
        
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "No Subject")
        sender = next((h['value'] for h in headers if h['name'] == 'From'), "Unknown Sender")
        
        body_text = ""
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data', '')
                    body_text += base64.urlsafe_b64decode(data).decode('utf-8')
        else:
            data = payload['body'].get('data', '')
            body_text = base64.urlsafe_b64decode(data).decode('utf-8')

        attachment_text = ""
        if 'parts' in payload:
            for part in payload['parts']:
                if part.get('filename') and part.get('filename').lower().endswith('.pdf'):
                    att_id = part['body'].get('attachmentId')
                    if att_id:
                        print(f"📎 Found PDF attachment: '{part['filename']}'. Parsing contents...")
                        attachment = service.users().messages().attachments().get(
                            userId='me', messageId=m['id'], id=att_id
                        ).execute()
                        file_data = base64.urlsafe_b64decode(attachment['data'].encode('UTF-8'))
                        
                        attachment_text += f"\n[EXTRACTED FROM ATTACHMENT {part['filename']}]:\n"
                        attachment_text += extract_text_from_pdf(file_data)

        combined_lower = (subject + body_text + attachment_text).lower()
        if "verification code" in combined_lower or "facebook" in combined_lower:
            continue

        print(f"📥 Retained financial data from: {sender}")
        valid_invoices.append({
            "sender": sender,
            "subject": subject,
            "email_body": body_text,
            "attachment_contents": attachment_text
        })

    return valid_invoices

async def main():
    invoices_to_process = get_all_unread_invoices()
    
    if not invoices_to_process:
        print("🏁 Everything clean! No new invoices found.")
        return

    model_client = OpenAIChatCompletionClient(
        model="gpt-4o-mini",
        base_url="https://models.inference.ai.azure.com",
        api_key=GITHUB_TOKEN
    )

    auditor_agent = AssistantAgent(
        name="Financial_Auditor",
        model_client=model_client,
        system_message="""You are the expert VP Finance Audit Executive. Map incoming billing content to precise General Ledger (GL) Codes - MUST only use these codes and no others.
        GL DIRECTORY:
        - 8010: Lease Payment to LHC/NHC/University (Vendor: LHCB)
        - 8024: Gas (Vendor: Texas Gas Service)
        - 8025: Electric (Vendor: City of Austin [Electric portion only], AAA Filter Service)
        - 8030: Water/Sewer (Vendor: City of Austin [Everything BUT electric], Global Water Technology)
        - 8040: Telephone (Vendor: Apogee Telecom)
        - 8050: Maintenance/Repair (Plumbing, leaks, building fixes)
        - 8060: Supplies (General house tools, supplies)
        - - 8070: Cleaning Service (Shining Cleaning, Oliver Termite. *CRITICAL RULE*: Oliver Termite invoices contain a line item called 'AAA Tech notes'. Do NOT confuse this with AAA Filter Service. Ignore the 'AAA' text and map the entire final total for the invoice to 8070. *Note for Virginia*: leave check in cubby)
        - 8080: Cable/Internet (Campus Connect/Apogee, Boldyn)
        - 8160: Trash (Central Texas Refuse, Break it Down, Republic Services)
        - 8170: Laundry (CSC, AutoChlor)
        - 8224: House Operations - Security (GuardTexas, AllSafe, Cothrons *Note*: if Cothrons != $330.31, add a note flagging it as a potential repair)
        - 9000: Kitchen Supplies (College Fresh 'Bill Back')
        - 9050: Food (Upper Crust standard monthly bill)

        STRICT CALCULATIONS:
        For City of Austin invoices, you must find the exact 'Electric' line item cost and assign it to 8025. Sum all other utility line items (Water, Sewer, Fees) and assign that remainder to 8030.
        If you cannot find a matching GL code, write 'MANUAL FLAG' in the GL Code column. Never make up a code not on this list.
        Locate the exact totals inside the email text or the attached document breakdown. Pass codes, vendor names, exact numerical dollar amounts, invoice number, and any notes to the Data_Formatter."""
    )

    formatter_agent = AssistantAgent(
        name="Data_Formatter",
        model_client=model_client,
        system_message="""You are the Billhighway Data Formatter. 
        Take the codes, vendor names, numerical totals, invoice number, and any notes provided by the Financial_Auditor.
        Format them into a clean Markdown table with these columns:
        | GL Code | Vendor/Line Item | Total Amount | | Invoice Number | Notes |
        Ensure the 'Total Amount' column contains the exact numerical financial values parsed. Output ONLY the markdown table."""
    )

    finance_team = RoundRobinGroupChat(
        participants=[auditor_agent, formatter_agent],
        max_turns=3
    )

    compiled_payload = ""
    for idx, inv in enumerate(invoices_to_process, start=1):
        compiled_payload += f"\n--- INVOICE #{idx} ---\nSender: {inv['sender']}\nSubject: {inv['subject']}\nEmail Body:\n{inv['email_body']}\n{inv['attachment_contents']}\n"

    task_instruction = f"""
    CRITICAL INSTRUCTION: You must compile a live Billhighway ledger sheet for this exact batch of emails. 
    Do NOT use dummy text, placeholders like '$XYZ', or templates under any circumstances. 

    For EVERY single invoice in the payload below, you must extract and output all of these details:
    1. The exact mapped GL Code.
    2. The REAL Vendor Name (e.g., 'Oliver Termite', 'City of Austin')
    3. The REAL, exact numerical total amount (e.g., '92.01'). If no numbers exist, write 'MANUAL FLAG' in the amount column.
    4. The REAL Invoice Number (e.g., 140586)
    4. Any required notes.

    Here is the live data payload to extract from:
    {compiled_payload}
    """

    print(f"\n⚙️ Analyzing {len(invoices_to_process)} invoices with your multi-agent team...")
    
    final_markdown_document = ""
    async for message in finance_team.run_stream(task=task_instruction):
        if hasattr(message, "source") and hasattr(message, "content"):
            print(f"[{message.source}] ──> Running analytical step...")
            if message.source == "Data_Formatter":
                final_markdown_document = message.content

    if final_markdown_document:
        # Save the raw Markdown file as a backup
        with open("chapter_invoice_summary.md", "w") as f:
            f.write("# Compiled Chapter Ledger Report\n\n")
            f.write(final_markdown_document)
            
        # Convert that Markdown into a professional PDF
        # Convert that Markdown into a professional PDF using WeasyPrint
        try:
            pdf_file_path = "chapter_invoice_summary.pdf"
            
            # 1. Convert the raw markdown table into actual HTML table tags
            html_table = markdown.markdown(final_markdown_document, extensions=['tables'])
            
            # 2. Wrap it in a beautiful, professional CSS stylesheet
            styled_html = f"""
            <html>
            <head>
            <style>
                body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; margin: 40px; color: #333; }}
                h1 {{ color: #2c3e50; text-align: center; font-size: 24px; }}
                hr {{ border: 0; height: 1px; background: #333; background-image: linear-gradient(to right, #ccc, #333, #ccc); margin-bottom: 30px; }}
                table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
                th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
                th {{ background-color: #f4f6f7; color: #2c3e50; font-weight: bold; text-transform: uppercase; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
            </style>
            </head>
            <body>
                <h1>AXO New Invoice Report</h1>
                <hr>
                {html_table}
            </body>
            </html>
            """
            
            # 3. Tell WeasyPrint to draw the PDF
            HTML(string=styled_html).write_pdf(pdf_file_path)
            
            print(f"\n🎉 Success! Review '{pdf_file_path}' in your folder to see your beautifully formatted report.")
        except Exception as e:
            print(f"\n⚠️ PDF generation failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())