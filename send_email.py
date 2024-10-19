import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email_self(subject: str, message: str) -> None:
    # Send/Receive 
    sender_email = "jaliuswelch@gmail.com"
    sender_password = "ugfn mjmd erzr jnjo"
    receiver_email = sender_email

    # Set up the SMTP server
    smtp_server = "smtp.gmail.com"
    port = 587  # For starttls

    # Create a secure SMTP connection
    server = smtplib.SMTP(smtp_server, port)
    server.starttls()
    server.login(sender_email, sender_password)

    # Create a multipart message and set headers
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject

    # Add message body
    msg.attach(MIMEText(message, 'plain'))

    # Send the email
    server.sendmail(sender_email, receiver_email, msg.as_string())

    # Close the SMTP server connection
    server.quit()

if __name__ == "__main__":
    subject = "Test Email"
    message = "This is a test email sent from Py"

    send_email_self(subject, message)
