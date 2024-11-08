import smtplib
import os

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import time

# SMTP email settings
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "SENDER_EMAIL"  # Your email address
SENDER_PASSWORD = "SENDER_PASSWORD"  # Your email password (or app-specific password)


def send_pin(email, pin):
    # Create email content
    subject = "Your PIN for Feedback Submission"
    body = f"Hello!\n\nYour PIN to submit feedback is: {pin}\n\nThis PIN is valid for 5 minutes."

    # Set up MIME
    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    # Send the email using SMTP
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, email, msg.as_string())
            print("PIN sent successfully to:", email)
    except Exception as e:
        print("Error sending email:", e)


def generate_pin():
    # Generate a random 6-digit PIN
    return str(random.randint(100000, 999999))


def verify_pin(input_pin, correct_pin, time_sent):
    # Check if the pin is correct and if it's within the time limit (5 minutes)
    current_time = time.time()
    if (
        input_pin == correct_pin and current_time - time_sent <= 300
    ):  # 300 seconds = 5 minutes
        return True
    return False


def collect_feedback():
    print("Please enter your email to receive a PIN:")
    email = input("Email: ")

    # Generate and send PIN
    pin = generate_pin()
    send_pin(email, pin)

    # Record the time the PIN was sent
    time_sent = time.time()

    # Ask the user to enter the PIN they received
    print(f"Please check your email for the PIN and enter it below.")
    input_pin = input("Enter PIN: ")

    # Verify the PIN and its validity
    if verify_pin(input_pin, pin, time_sent):
        print("PIN verified! You can now leave your feedback.")
        feedback = input("Please enter your feedback: ")
        print("Thank you for your feedback!")
        # Here, you can save feedback to a file or database
    else:
        print("Invalid or expired PIN. Please try again.")


if __name__ == "__main__":
    collect_feedback()
