from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button


class PairwiseConnection(GridLayout):
    '''
    Displays the pairwise connections between users in the App
    '''
    rows = 1

    def __init__(self, **kwargs):
        super(PairwiseConnection, self).__init__()
        if kwargs['type'] == 'S':
            self.agent = kwargs['agent']
            self.cred = kwargs['credential']
            self.myDID = kwargs['myDID']
            self.LOOP = kwargs['loop']
        self.DID = kwargs['DID']
        self.name = kwargs['name']

        # sending request to other user
        def med_btn(instance):
            print("med_btn")
            print("AGENT:", self.agent.owner)
            self.LOOP.run_until_complete(self.cred.generate_credential_offer('medical', self.DID, self.myDID, self.name))

        # sending response to other user
        def cred_btn(instance):
            print("Send cred btn")
            self.LOOP.run_until_complete(self.cred.generate_credential_offer('consent', self.DID, self.myDID, self.name))

        name = FloatLayout()
        name_label = Label(text=kwargs['name'], color=(0, 0, 0, 1),size_hint=(1,.2),pos_hint={"top":1,"right":1})
        name.add_widget(name_label)

        theirDID = FloatLayout()
        theirDID_label = Label(text=self.DID, color=(0, 0, 0, 1), size_hint=(1, .2), pos_hint={"top": 1, "right": 1})
        theirDID.add_widget(theirDID_label)

        if kwargs['type'] == "S":
            myDID = FloatLayout()
            myDID_label = Label(text=self.myDID, color=(0, 0, 0, 1), size_hint=(1, .2), pos_hint={"top": 1, "right": 1})
            myDID.add_widget(myDID_label)

        action = FloatLayout()
        medBtn = Button(text="Medical", font_size=9, size_hint=(1, .2), pos_hint={"top": 1, "right": 1})
        medBtn.bind(on_release=med_btn)
        action.add_widget(medBtn)
        action2 = FloatLayout()
        credBtn = Button(text="Credential", font_size=9, size_hint=(1, .2), pos_hint={"top": 1, "right": 1})
        credBtn.bind(on_release=cred_btn)
        action2.add_widget(credBtn)

        self.add_widget(name)
        if kwargs['type'] == 'R':
            self.add_widget(theirDID)
        if kwargs['type'] == 'S':
            self.add_widget(action)
            self.add_widget(action2)
