from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.button import Button
import json


class PendingConnection(GridLayout):
    '''
    Displays pending connections between users in the app.
    '''
    rows = 1

    def __init__(self, **kwargs):
        super(PendingConnection, self).__init__()
        self.agent = kwargs['agent']
        self.connection = kwargs['connection']
        self.invitation = kwargs['invitation']
        self.loop = kwargs['loop']

        def showpopup(instance):
            history = json.dumps(kwargs['history'], indent=4)
            pop = Popup(title="History", content=Label(text=history, size_hint=(1, 1), size=(200, 300)))
            pop.open()

        # sending request to other user
        def send_rqst(instance):
            print("SEND REQUEST", self.invitation)
            print("AGENT:", self.agent.owner)
            self.loop.run_until_complete(self.connection.send_request(self.invitation))
            # self.agent.send_request(self.invitation)
            pass

        # sending response to other user
        def send_rspd(instance):
            print("Send response", self.invitation)
            self.loop.run_until_complete(self.connection.send_response(self.invitation))
            pass
        # sets as a request or as a response
        if kwargs['status'] == 'Invite Received':
            request = "Send Request"
        elif kwargs['status'] == 'Request Received':
            request = "Send Response"
        else:
            request = "N/A"

        connection_key = FloatLayout()
        connection_label = Label(text=kwargs['connection_key'], color=(0, 0, 0, 1), font_size=6,size_hint=(1,.2),
                                 pos_hint={"top": 1,"right": 1})
        connection_key.add_widget(connection_label)

        title = FloatLayout()
        label_label = Label(text=kwargs['title'], color=(0, 0, 0, 1), font_size=9, size_hint=(1, .2), pos_hint={"top": 1, "right": 1})
        title.add_widget(label_label)

        status = FloatLayout()
        status_label = Label(text=kwargs['status'], color=(0, 0, 0, 1),font_size=9 ,size_hint=(1, .2), pos_hint={"top": 1, "right": 1})
        status.add_widget(status_label)

        history = FloatLayout()
        history_button = Button(text='History', font_size=9,size_hint=(1, .2), pos_hint={"top": 1, "right": 1})
        history_button.bind(on_release=showpopup)
        history.add_widget(history_button)

        action = FloatLayout()
        action_button = Button(text=request, font_size=9, size_hint=(1, .2), pos_hint={"top": 1, "right": 1})

        # depending on the request, the button will display the action
        if request == "Send Request":
            action_button.bind(on_release=send_rqst)
        elif request == "Send Response":
            action_button.bind(on_release=send_rspd)
        if request == 'Send Request' or request == 'Send Response':
            action.add_widget(action_button)

        self.add_widget(connection_key)
        self.add_widget(title)
        self.add_widget(status)
        self.add_widget(history)
        self.add_widget(action)
