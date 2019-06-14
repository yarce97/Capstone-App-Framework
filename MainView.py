from kivy.app import App
from kivy.uix.button import ButtonBehavior
from kivy.uix.image import Image
from kivy.lang import Builder
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.properties import ObjectProperty
from kivy.uix.screenmanager import ScreenManager, Screen

import asyncio
from agent import Agent
from steward import Steward
import helper
from modules.connection import Connection
from modules.credential import Credential
from modules.proof import Proof
from credential_page import CredentialPage, CredentialView
from pending_connection import PendingConnection
from pairwise_connection import PairwiseConnection
import socket_client


class LoginWindow(Screen):
    '''
        The login window allows the user to enter their wallet name as well the passphrase
        associated with the wallet in order to login. The passphrase is tested against the
        MEWS's password verification of the mobile security framework.
    '''
    walletName = ObjectProperty(None)  # name of agent (wallet)
    passphrase = ObjectProperty(None) # passphrase for wallet
    patient = ObjectProperty(None)  # type of patient
    doctor = ObjectProperty(None)
    state = ObjectProperty(None)

    def login_btn(self):
        '''
            When clicking on the submit button, the text entered is tested and the type of
            user is set.
        :return:
        '''
        temp = self.verify_check_boxes()
        global AGENT        # Agent user
        AGENT = temp
        print(AGENT.type)
        passed, exception_msg = helper.verify_input(self.walletName.text, self.passphrase.text)     # verify user
        if passed:  # if no exception occurs
            # open wallet
            open_wallet = LOOP.run_until_complete(AGENT.connect_wallet(self.walletName.text, self.passphrase.text))
            if open_wallet:
                # open pool
                open_pool = LOOP.run_until_complete(AGENT.connect_to_pool())
                if open_pool:
                    if AGENT.type == 'State':
                        LOOP.run_until_complete(AGENT.generate_and_store_steward_id())
                        LOOP.run_until_complete(AGENT.generate_and_store_trustanchor_ids())
                        LOOP.run_until_complete(AGENT.steward_adds_trust_anchors_to_ledger())
                        LOOP.run_until_complete(AGENT.state_builds_medical_schema())
                        LOOP.run_until_complete(AGENT.hospital_builds_patient_consent())
                    self.reset()
                    global CONNECTION, CREDENTIAL, PROOF        # start Connection, Credential, and Proof classes
                    CONNECTION = Connection(AGENT)
                    CREDENTIAL = Credential(AGENT)
                    PROOF = Proof(AGENT)
                    wm.current = "userPage"     # move to user page
                else:
                    invalid_login("Could not connect to pool.\nPlease Try Again")
                    self.reset()
                    wm.current = "main"
            else:
                invalid_login("Wallet Name or passphrase are incorrect. \nPlease Try Again.")
                self.reset()
                wm.current = "main"
        else:
            invalid_login(exception_msg)
            self.reset()
            wm.current = "main"

    def verify_check_boxes(self):
        """
        Checks the type of user checked
        """
        if self.patient.active:
            print("patient")
            AGENT = Agent('Patient')
        elif self.doctor.active:
            print("doctor")
            AGENT = Agent('Doctor')
        elif self.state.active:
            print("state")
            AGENT = Steward('State')
        else:
            print("none selected")
            invalid_login("Must select type of user.")
            self.reset()
            wm.current = "main"
        return AGENT

    def reset(self):
        # resets the text entered
        self.walletName.text = ""
        self.passphrase.text = ""


# for images used for the button
class ImageButton(ButtonBehavior, Image):
    pass


class UserPage(Screen):
    """
    User page displays all the different types of actions that could be done
    """
    n = ObjectProperty(None)

    def on_enter(self, *args):
        """
        Display the name of the wallet
        """
        if AGENT.initialized:
            name = LOOP.run_until_complete(AGENT.get_agent_name())
            self.n.text = AGENT.type + ": " + name
        if AGENT.type == 'State':
            print("state trust anchor: ", AGENT.state_trust_anchor_did)
            print("hospG trust anchor: ", AGENT.hospG_trust_anchor_did)
            print("hospB trust anchor: ", AGENT.hospB_trust_anchor_did)

    # go to relationships page when button pressed
    def relationships(self):
        wm.current = "relationships"

    # logout when button pressed
    def logout(self):
        wm.current = "main"

    # go to connect to server  page when button pressed
    def connect_server(self):
        wm.current = "connectServer"

    # go to delete wallet when button pressed
    def delete_wallet(self):
        wm.current = "deleteWalletPage"

    # go to schemas page when button pressed
    def schemas(self):
        wm.current = "schemaPage"

    # go to credentials page when button pressed
    def credentials(self):
        wm.current = "credentialsPage"

    # go to prove page when button pressed
    def prove(self):
        wm.current = "provePage"

class DeleteWalletPage(Screen):
    '''
    When user deletes their wallet they must supply the wallet name as well as the passphrase
    '''
    walletName = ObjectProperty(None)  # name of agent (wallet)
    passphrase = ObjectProperty(None)
    result_delete = ObjectProperty(None)

    # return to users page
    def back(self):
        wm.current = "userPage"

    def remove_wallet(self):
        """
        Remove wallet by providing the wallet name and passphrase
        """
        if self.walletName.text != "" or self.passphrase.text != "":
            if LOOP.run_until_complete(AGENT.delete_wallet(self.walletName.text, self.passphrase.text)):
                wm.current = "main"
            else:
                self.result_delete.text = "Unable to remove agent"
                print("COULD NOT REMOVE AGENT")
        else:
            self.result_delete.text = "Fill all text areas"


class RelationshipPage(Screen):
    '''
    Create a connection with another user that is connected to the same server. The user must have connected to the
    server in order for the processes to be completed.
    '''
    n = ObjectProperty(None)

    #return to users page
    def back(self):
        wm.current = "userPage"

    def on_enter(self, *args):
        """
        When the page is loaded, the wallet name is displayed as well the pending connections and the connections.
        """
        if AGENT.initialized:
            name = LOOP.run_until_complete(AGENT.get_agent_name())      # get name of agent
            self.n.text = AGENT.type + ": " + name
            # get invitations
            invitations = LOOP.run_until_complete(AGENT.get_invitations())  # get invitations sent out
            pending_id = self.ids['pendingConnection']
            pending_id.clear_widgets()
            for invitation in invitations:
                p = PendingConnection(connection_key=invitation.get('connection_key'),
                                      title=invitation.get('label'),
                                      status=invitation.get('status'),
                                      history=invitation.get('history'),
                                      invitation=invitation,
                                      agent=AGENT,
                                      connection=CONNECTION,
                                      loop=LOOP)
                pending_id.add_widget(p)
            # get pairwise connections
            pairwise_records = LOOP.run_until_complete((AGENT.get_pairwise_connections())) # get connections established
            print("PAIRWISE: ", pairwise_records)
            pairwise_id = self.ids['pairwiseConnection']
            pairwise_id.clear_widgets()
            for pair in pairwise_records:
                p = PairwiseConnection(name=pair.get('metadata').get('label'),
                                       DID=pair.get('their_did'),
                                       type="R")
                pairwise_id.add_widget(p)

    # go to generate connection page
    def generate_connection(self):
        wm.current = "generateConnection"

    # go to recieve invite page
    def recieveInvite(self):
        wm.current = "recieveInvitation"


class ConnectServer(Screen):
    '''
    Connecting to server required for the server to be running.
    The IP and the port number much match for all the users.
    '''
    ip = ObjectProperty(None)
    port = ObjectProperty(None)
    agent = ObjectProperty(None)
    connected = ObjectProperty(None)

    def on_enter(self, *args):
        name = LOOP.run_until_complete(AGENT.get_agent_name())
        self.agent.text = AGENT.type + ": " + name

    def back(self):
        self.ip.text = ""
        self.port.text = ""
        wm.current = "userPage"

    def start_server(self):
        """
        When clicking on connect button, it will try t connect to the server with the IP and port number entered.
        """
        print("start server")
        port = int(self.port.text)
        ip = self.ip.text
        username = self.agent.text

        if not socket_client.connect(ip, port, username, show_error):
            print("not connected")
            self.connected.text = "Not connected"
        else:
            print("connected to server")
            self.connected.text = "Connected"
            self.ip.text = ""
            self.port.text = ""
            socket_client.start_listening(self.incoming_message, show_error)

    def incoming_message(self, username, message):
        '''
        Function listens for incoming messages being sent. It checks what type of message it is in order
        to follow the correct function.
        '''
        print(f'\n\n{username}:   {message}')
        msg = LOOP.run_until_complete(AGENT.read_msg(message))      # message read
        print("\nMESSAGE: ", msg)
        print("MSG TYPE: ", msg.type)
        type = msg.type                 # type of message
        sendTo = msg.sendTo         # who the message is being sent to
        print("SENDTO: ", sendTo)
        print("agent: ", AGENT.owner)
        if type == "SEND_REQUEST" and sendTo == AGENT.owner:
            LOOP.run_until_complete(CONNECTION.request_recieved(msg))
        elif type == "SEND_RESPONSE" and sendTo == AGENT.owner:
            LOOP.run_until_complete(CONNECTION.response_recieved(msg))
        elif type == "credential_offer" and sendTo == AGENT.owner:
            LOOP.run_until_complete(CREDENTIAL.credential_offer(msg))
        elif type == "credential_request" and sendTo == AGENT.owner:
            LOOP.run_until_complete(CREDENTIAL.credential_request(msg))
        elif type == "credential" and sendTo == AGENT.owner:
            LOOP.run_until_complete(CREDENTIAL.credential_received(msg))
        elif type == "proof_offer" and sendTo == AGENT.owner:
            LOOP.run_until_complete(PROOF.proof_offer(msg))
        elif type == "proof_request" and sendTo == AGENT.owner:
            LOOP.run_until_complete(PROOF.proof_request(msg))
        elif type == "proof" and sendTo == AGENT.owner:
            LOOP.run_until_complete(PROOF.proof_received(msg))
        else:
            print("other request: ", msg)


class GenerateConnection(Screen):
    """
    The generate connection page will display a code that is created and can be sent to a user by email.
    """
    code = ObjectProperty(None)
    agent = ObjectProperty(None)
    senderEmail = ObjectProperty(None)
    code_gen = ObjectProperty(None)

    def on_enter(self, *args):
        self.agent.text = AGENT.type + ": " + LOOP.run_until_complete(AGENT.get_agent_name())
        key = LOOP.run_until_complete(CONNECTION.generate_invite())
        self.code.text = "Code Generated: \n" + key

    def sendEmail(self):
        '''
        Sends the code to the email provided
        '''
        if helper.sendEmail(self.senderEmail.text, self.code.text, self.agent.text):
            self.code_gen.text = "SENT"

    def back(self):
        self.senderEmail.text = ""
        self.code.text = ""
        self.code_gen.text = ""
        wm.current = "relationships"


class RecieveInvitation(Screen):
    '''
    The user enters the code provided to generate the connection between the users.
    '''
    agent = ObjectProperty(None)
    copyCode = ObjectProperty(None)
    rec = ObjectProperty(None)

    def on_enter(self, *args):
        self.agent.text = AGENT.type + ": " + LOOP.run_until_complete(AGENT.get_agent_name())

    def back(self):
        self.copyCode.text = ""
        self.rec.text = ""
        wm.current = "relationships"

    def receiveCode(self):
        if self.copyCode.text != "":
            LOOP.run_until_complete(CONNECTION.recieve_invite(self.copyCode.text))
        self.rec.text = "RECEIVED"

class SchemaPage(Screen):
    '''
    The schema page will display the information of the connections generated and the types of
    information that can be sent only by the state/hospital.
    '''
    n = ObjectProperty(None)

    def on_enter(self, *args):
        name = LOOP.run_until_complete(AGENT.get_agent_name())
        self.n.text = AGENT.type + ": " + name
        # connections
        pairwise_records = LOOP.run_until_complete((AGENT.get_pairwise_connections())) # get connections established
        print("PAIRWISE: ", pairwise_records)
        pairwise_id = self.ids['pairwiseConnections']
        pairwise_id.clear_widgets()
        for pair in pairwise_records:
            p = PairwiseConnection(name=pair.get('metadata').get('label'),
                                   DID=pair.get('their_did'),
                                   myDID=pair.get('my_did'),
                                   type="S",
                                   agent=AGENT,
                                   credential=CREDENTIAL,
                                   loop=LOOP)
            pairwise_id.add_widget(p)

    def back(self):
        wm.current = "userPage"


class CredentialsPage(Screen):
    '''
    The credentials page will show the connections generated as well the credentials that have been sent by the
    hospital/state for the patient or doctor.
    '''
    n = ObjectProperty(None)

    def on_enter(self, *args):
        name = LOOP.run_until_complete(AGENT.get_agent_name())
        self.n.text = AGENT.type + ": " + name
        pairwise_records = LOOP.run_until_complete((AGENT.get_pairwise_connections())) # get connections established
        print("PAIRWISE: ", pairwise_records)
        pairwise_id = self.ids['schema_pairwise']
        pairwise_id.clear_widgets()
        for pair in pairwise_records:
            p = CredentialPage(name=pair.get('metadata').get('label'),
                               DID=pair.get('their_did'),
                               myDID=pair.get('my_did'),
                               agent=AGENT,
                               credential=CREDENTIAL,
                               proof=PROOF,
                               loop=LOOP)
            pairwise_id.add_widget(p)
        cred_id = self.ids['cred_layout']
        cred_id.clear_widgets()
        temp = CredentialView(agent=AGENT)
        cred_id.add_widget(temp)

    def back(self):
        wm.current = "userPage"


class ProvePage(Screen):
    '''
    Prove page allows the patient to enter the hospital and state trust anchor in order for the patient to be able to
    receive the credentials from the doctor.
    '''
    n = ObjectProperty(None)
    stateAnchor = ObjectProperty(None)
    hospitalAnchor = ObjectProperty(None)

    def on_enter(self, *args):
        name = LOOP.run_until_complete(AGENT.get_agent_name())
        self.n.text = AGENT.type + ": " + name

    def back(self):
        wm.current = "userPage"

    def trusted_anchor(self):
        '''
        Set the trust anchors for the patient
        '''
        if self.stateAnchor.text != "" and self.hospitalAnchor.text != "":
            AGENT.State_TA_DID = self.stateAnchor.text
            AGENT.Hospital_TA_DID = self.hospitalAnchor.text
            self.hospitalAnchor.text = ""
            self.stateAnchor.text = ""

# keeps track of the pages created
class WindowManager(ScreenManager):
    pass


# Login error popup
def invalid_login(exception_msg):
    pop = Popup(title="Invalid Login", content=Label(text=exception_msg),
                size_hint=(None, None), size=(350, 300))
    pop.open()


SERVER_STARTED = False
kv = Builder.load_file("main.kv")
wm = WindowManager()
screens = [LoginWindow(name="main"),
           UserPage(name="userPage"),
           RelationshipPage(name="relationships"),
           GenerateConnection(name="generateConnection"),
           RecieveInvitation(name="recieveInvitation"),
           ConnectServer(name="connectServer"),
           SchemaPage(name="schemaPage"),
           CredentialsPage(name="credentialsPage"),
           ProvePage(name="provePage"),
           DeleteWalletPage(name="deleteWalletPage"),]
for screen in screens:
    wm.add_widget(screen)
wm.current = "main"     # set main as the starting page


class MyMainApp(App):
    '''
    Start running the app
    '''
    def build(self):
        return wm


# prints errors
def show_error(message):
    print(message)


if __name__ == "__main__":
    LOOP = asyncio.get_event_loop()
    global AGENT, CONNECTION
    AGENT = None
    CONNECTION = None
    try:
        LOOP.create_task(MyMainApp().run())  # start app
    except KeyboardInterrupt:
        print("exiting")
