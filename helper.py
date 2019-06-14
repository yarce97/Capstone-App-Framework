# helper class verifies the input and sends the email to user
import os
import smtplib
from email.message import EmailMessage
os.environ['CLASSPATH'] = "./mobile_security_framework/mhealthsecurityframework.jar"
from jnius import autoclass


def verify_input(walletName, passphrase):
    '''
    Function checks if the input is not empty and it also checks the password verification function of the
    mobile security app framework
    :param walletName: name of wallet entered
    :param passphrase: password
    :return: boolean (pass) and error message
    '''
    if walletName == "" or passphrase == "":
        return False, "Invalid Input"
    password = autoclass('edu.uw.medhas.mhealthsecurityframework.password.PasswordUtils')
    Password = password()       # mobile app framework password
    try:
        Password.validatePassword(passphrase)
    except Exception as e:
        if str(e) == "JVM exception occurred: edu.uw.medhas.mhealthsecurityframework.password.exception.PasswordTooShortException":
            return False, "Password Is Too Short. \nMust be at least 8 characters long.\n Please Try Again."
        elif str(e) == "JVM exception occurred: edu.uw.medhas.mhealthsecurityframework.password.exception.PasswordNoUpperCaseCharacterException":
            return False, "Password Contains No Upper Case Character. \nPlease Try Again."
        elif str(e) == "JVM exception occurred: edu.uw.medhas.mhealthsecurityframework.password.exception.PasswordNoLowerCaseCharacterException":
            return False,  "Password Contains No Lower Case Character. \nPlease Try Again."
        elif str(e) == "JVM exception occurred: edu.uw.medhas.mhealthsecurityframework.password.exception.PasswordNoNumberCharacterException":
            return False, "Password Contains No Number Character.\nPlease Try Again."
        elif str(e) == "JVM exception occurred: edu.uw.medhas.mhealthsecurityframework.password.exception.PasswordNoSpecialCharacterException":
            return False, "Password Contains No Special Character. \nPlease Try Again."
        else:
            return False, "Other error: ", e
    return True, "No Exception"


def sendEmail(receiver_email, code, agent):
    '''
    sends email to the designated email address.
    *The email it is send from needs to be modified and parameters changed
    :param receiver_email: email to send to
    :param code: code generated
    :param agent: name of the agent
    :return: true
    '''
    # change to have user give their own email address and not send from mine
    SENDER_EMAIL_ADDRESS = os.environ.get('EMAIL_ADDRESS')
    EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
    print(SENDER_EMAIL_ADDRESS)
    print(EMAIL_PASSWORD)
    request = "Please enter code provided into MedIC portal's Request Invitation:\n"
    msg = EmailMessage()
    msg['Subject'] = "Invitation Request from" + agent
    msg['From'] = SENDER_EMAIL_ADDRESS
    msg['To'] = receiver_email
    msg.set_content(request + code)
    # send message to email
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(SENDER_EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)
    return True

