import os.path
import base64
import time
import threading
from datetime import datetime, timedelta
from tkinter import Tk, Frame, Button, Label, Scrollbar, Text, Toplevel, Canvas, VERTICAL, RIGHT, LEFT, BOTH, NW, END, Radiobutton, IntVar
from tkinter import ttk
from tkinter.font import Font
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

class EmailCheckerApp:
    def __init__(self, root, time_window):
        self.root = root
        self.root.title("Email Checker")
        self.root.geometry("1200x700")
        self.root.configure(bg='white')

        self.time_window = time_window
        self.keyword_mapping = {
            "Rejected": ["unfortunately", "we will not"],
            "Accepted": [ "interview"]
        }
        self.email_buttons = {category: {"Unread": [], "Read": []} for category in self.keyword_mapping.keys()}
        self.creds = self.authenticate_gmail()
        self.service = build('gmail', 'v1', credentials=self.creds)

        self.custom_font = Font(family="Helvetica", size=14, weight="bold")
        self.create_interface()
        self.check_emails()

    def authenticate_gmail(self):
        creds = None
        creds_path = os.path.join(os.path.dirname(__file__), 'credentials.json')
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                creds = flow.run_local_server(port=0)
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        return creds

    def create_interface(self):
        self.frames = {}
        self.labels = {}
        categories = list(self.keyword_mapping.keys())

        # Create the column headers
        Label(self.root, text="", font=("Helvetica", 18, "bold"), bg='white').grid(row=0, column=0, padx=20, pady=10, sticky="nsew")
        for idx, category in enumerate(categories):
            header_label = Label(self.root, text=category, font=self.custom_font, bg='white')
            header_label.grid(row=0, column=idx+1, padx=20, pady=10, sticky="nsew")

        # Create the row headers
        row_headers = ["Unread Emails", "Read Emails"]
        for row, header in enumerate(row_headers):
            row_label = Label(self.root, text=header, font=self.custom_font, bg='white')
            row_label.grid(row=row+1, column=0, padx=20, pady=10, sticky="nsew")
        
        # Create the frames for data
        for row, status in enumerate(["Unread", "Read"]):
            for col, category in enumerate(categories):
                frame = Frame(self.root, bg='white')
                frame.grid(row=row+1, column=col+1, padx=20, pady=10, sticky="nsew")

                canvas = Canvas(frame, bg='white')
                scrollbar = Scrollbar(frame, orient=VERTICAL, command=canvas.yview)
                scrollable_frame = Frame(canvas, bg='white')

                scrollable_frame.bind(
                    "<Configure>",
                    lambda e, canvas=canvas: canvas.configure(
                        scrollregion=canvas.bbox("all")
                    )
                )

                canvas.create_window((0, 0), window=scrollable_frame, anchor=NW)
                canvas.configure(yscrollcommand=scrollbar.set)

                canvas.pack(side=LEFT, fill=BOTH, expand=True)
                scrollbar.pack(side=RIGHT, fill=BOTH)

                self.frames[f"{category}_{status.lower()}"] = scrollable_frame

        # Add the progress bar
        self.progress = ttk.Progressbar(self.root, orient="horizontal", length=200, mode="determinate")
        self.progress.grid(row=4, columnspan=3, pady=10)

        # Add the loading label
        self.loading_label = Label(self.root, text="Loading results", font=("Helvetica", 12), bg='white')
        self.loading_label.grid(row=5, columnspan=3, pady=10)

    def check_emails(self):
        threading.Thread(target=self.fetch_emails, daemon=True).start()

    def fetch_emails(self):
        categories = list(self.keyword_mapping.keys())
        total_steps = len(categories) * 2  # Two steps for each category (unread and read)
        step = 0

        for category, keywords in self.keyword_mapping.items():
            print(f"Processing {category} Unread Emails")
            self.update_email_buttons(category, "unread", keywords)
            step += 1
            self.progress["value"] = (step / total_steps) * 100
            self.root.update_idletasks()

            print(f"Processing {category} Read Emails")
            self.update_email_buttons(category, "read", keywords, max_results=5)
            step += 1
            self.progress["value"] = (step / total_steps) * 100
            self.root.update_idletasks()

        self.progress["value"] = 100
        self.loading_label.config(text="Loading complete")
        self.root.update_idletasks()

    def update_email_buttons(self, category, status, keywords, max_results=None):
        time_window_ago = datetime.now() - timedelta(days=self.time_window*30)
        after_date = time_window_ago.strftime('%Y/%m/%d')
        query = f"after:{after_date} " + " OR ".join([f"in:inbox is:{status} {keyword}" for keyword in keywords])
        messages = self.get_emails(query, max_results)

        frame_key = f"{category}_{status.lower()}"
        frame = self.frames[frame_key]
        
        for widget in frame.winfo_children():
            widget.destroy()

        if not messages:
            print(f"No {status} emails found for {category}")
            Label(frame, text="No new unread emails in this category" if status == "unread" else "No emails found", font=("Helvetica", 12), bg='white').pack()
        else:
            print(f"Found {len(messages)} {status} emails for {category}")
            for msg in messages:
                msg_id = msg['id']
                sender, content = self.get_email_details(msg_id)
                if any(kw.lower() in content.lower() for kw in keywords):
                    button = Button(frame, text=sender, command=lambda msg_id=msg_id: self.show_email_content(msg_id), bg='white')
                    button.pack(pady=5)
                    self.email_buttons[category][status.capitalize()].append(button)

    def get_emails(self, query, max_results=None):
        try:
            results = self.service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
            messages = results.get('messages', [])
            return messages
        except Exception as e:
            print(f"An error occurred: {e}")
            return []

    def get_email_details(self, msg_id):
        try:
            message = self.service.users().messages().get(userId='me', id=msg_id).execute()
            payload = message.get('payload', {})
            headers = payload.get('headers', [])
            parts = payload.get('parts', [])
            data = None
            sender = "Unknown Sender"
            for header in headers:
                if header['name'] == 'From':
                    sender = header['value']
                    break

            for part in parts:
                if part['mimeType'] == 'text/plain':
                    data = part['body']['data']
                    break

            if data:
                decoded_data = base64.urlsafe_b64decode(data.encode('UTF-8')).decode('UTF-8')
                return sender, decoded_data
            return sender, "No content available"
        except Exception as e:
            print(f"An error occurred: {e}")
            return "Unknown Sender", "No content available"

    def show_email_content(self, msg_id):
        sender, content = self.get_email_details(msg_id)
        top = Toplevel(self.root)
        top.title(f"Email from {sender}")
        top.geometry("600x400")
        scrollbar = Scrollbar(top, orient=VERTICAL)
        scrollbar.pack(side=RIGHT, fill=BOTH)
        text = Text(top, wrap='word', yscrollcommand=scrollbar.set, bg='white')
        text.insert(END, content)
        text.pack(expand=True, fill=BOTH)
        scrollbar.config(command=text.yview)

def select_time_window():
    def on_submit():
        time_window = time_window_var.get()
        selection_window.destroy()
        main_window = Tk()
        EmailCheckerApp(main_window, time_window)
        main_window.mainloop()

    selection_window = Tk()
    selection_window.title("Select Time Window")
    selection_window.geometry("400x300")
    selection_window.configure(bg='white')

    Label(selection_window, text="Please provide a time window for which you would like to track your applications", font=("Helvetica", 14), bg='white', wraplength=350).pack(pady=20)

    time_window_var = IntVar(value=4)
    options = [2, 4, 6, 12]

    for option in options:
        Radiobutton(selection_window, text=f"{option} months", variable=time_window_var, value=option, font=("Helvetica", 12), bg='white').pack(anchor='w', padx=20)

    Button(selection_window, text="Submit", command=on_submit, font=("Helvetica", 12), bg='white').pack(pady=20)

    selection_window.mainloop()

if __name__ == '__main__':
    select_time_window()
