from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button


class CredentialPage(GridLayout):
    '''
    Class displays the connections between users in the Credentials page of the app
    '''
    rows = 1

    def __init__(self, **kwargs):
        super(CredentialPage, self).__init__()
        self.agent = kwargs['agent']
        self.cred = kwargs['credential']
        self.myDID = kwargs['myDID']
        self.name = kwargs['name']
        self.proof = kwargs['proof']
        self.LOOP = kwargs['loop']

        # sending response to other user
        def offer_btn(instance):
            print("offer proof")
            self.LOOP.run_until_complete(self.proof.generate_proof_offer(self.DID, self.myDID, self.name,
                                                                         self.agent.owner))
        #display name, DIDs, and buttons
        name = FloatLayout()
        name_label = Label(text=kwargs['name'], color=(0, 0, 0, 1),size_hint=(1,.2),pos_hint={"top":1,"right":1})
        name.add_widget(name_label)

        myDID = FloatLayout()
        myDID_label = Label(text=kwargs['myDID'], color=(0, 0, 0, 1), size_hint=(1, .2), pos_hint={"top": 1, "right": 1})
        myDID.add_widget(myDID_label)

        action = FloatLayout()
        offerBtn = Button(text="Offer Proof", font_size=9, size_hint=(1, .2), pos_hint={"top": 1, "right": 1})
        offerBtn.bind(on_release=offer_btn)
        action.add_widget(offerBtn)

        self.add_widget(name)
        #self.add_widget(myDID)
        self.add_widget(action)


class CredentialView(GridLayout):
    '''
    Displays the credentials that have been sent from the hospital/state. Needs to be modified to take in
    parameters and not have them hardcoded.
    '''
    rows = 8
    cols = 2

    def __init__(self, **kwargs):
        super(CredentialView, self).__init__()
        self.agent = kwargs['agent']
        self.med = self.agent.get_med_cred()
        self.con = self.agent.get_consent_cred()
        if self.con:
            print("CONSENT CRED: ", self.con)
            one = "Patient Consent"
            two = ""
            three = "First Name: Alice"
            four = ""
            five = "Last Name: Garcia"
            six = ""
            seven = "Credential Requirement: Doctor"
            eight = ""
            nine = "Hospital Affiliation: True"
            ten = ""
            eleven = "Pace: True"
            twelve = ""
            thirteen = "Defib: False"
            fourteen = ""
            fifteen = "Signed At: Hospital Green:"
            sixteen = ""
        elif self.med:
            print("MED CRED: ", self.med)
            one = "Medical Credential"
            two = "Hospital Affiliation"
            three = "First Name: Bob"
            four = "First Name: Bob"
            five = "Last Name: Smith"
            six = "Last Name: Smith"
            seven = "Degree: Nurse"
            eight = "Hospital: Hospital Blue"
            nine = "Level: Heart Specialist"
            ten = "Start Date: 15-07-01"
            eleven = "Year: 2015"
            twelve = "End Date: None"
            thirteen = "Status: good"
            fourteen = ""
            fifteen = ""
            sixteen = ""
        else:
            print("NO CRED")
            one = ""
            two = ""
            three = ""
            four = ""
            five = ""
            six = ""
            seven = ""
            eight = ""
            nine = ""
            ten = ""
            eleven = ""
            twelve = ""
            thirteen = ""
            fourteen = ""
            fifteen = ""
            sixteen = ""

        title = FloatLayout()
        title_label = Label(text=one, bold=True, color=(0, 0, 0, 1),size_hint=(1,.2),pos_hint={"top":1,"right":1})
        title.add_widget(title_label)

        empty = FloatLayout()
        empty_label = Label(text=two, color=(0, 0, 0, 1),size_hint=(1,.2),pos_hint={"top":1,"right":1})
        empty.add_widget(empty_label)

        p1 = FloatLayout()
        p1_label = Label(text=three, color=(0, 0, 0, 1),size_hint=(1,.2),pos_hint={"top":1,"right":1})
        p1.add_widget(p1_label)

        p1a = FloatLayout()
        p1a_label = Label(text=four, color=(0, 0, 0, 1),size_hint=(1,.2),pos_hint={"top":1,"right":1})
        p1a.add_widget(p1a_label)

        p2 = FloatLayout()
        p2_label = Label(text=five, color=(0, 0, 0, 1),size_hint=(1,.2),pos_hint={"top":1,"right":1})
        p2.add_widget(p2_label)

        p2a = FloatLayout()
        p2a_label = Label(text=six, color=(0, 0, 0, 1),size_hint=(1,.2),pos_hint={"top":1,"right":1})
        p2a.add_widget(p2a_label)

        p3 = FloatLayout()
        p3_label = Label(text=seven, color=(0, 0, 0, 1),size_hint=(1,.2),pos_hint={"top":1,"right":1})
        p3.add_widget(p3_label)

        p3a = FloatLayout()
        p3a_label = Label(text=eight, color=(0, 0, 0, 1),size_hint=(1,.2),pos_hint={"top":1,"right":1})
        p3a.add_widget(p3a_label)

        p4 = FloatLayout()
        p4_label = Label(text=nine, color=(0, 0, 0, 1),size_hint=(1,.2),pos_hint={"top":1,"right":1})
        p4.add_widget(p4_label)

        p4a = FloatLayout()
        p4a_label = Label(text=ten, color=(0, 0, 0, 1),size_hint=(1,.2),pos_hint={"top":1,"right":1})
        p4a.add_widget(p4a_label)

        p5 = FloatLayout()
        p5_label = Label(text=eleven, color=(0, 0, 0, 1),size_hint=(1,.2),pos_hint={"top":1,"right":1})
        p5.add_widget(p5_label)

        p5a = FloatLayout()
        p5a_label = Label(text=twelve, color=(0, 0, 0, 1),size_hint=(1,.2),pos_hint={"top":1,"right":1})
        p5a.add_widget(p5a_label)

        p6 = FloatLayout()
        p6_label = Label(text=thirteen, color=(0, 0, 0, 1),size_hint=(1,.2),pos_hint={"top":1,"right":1})
        p6.add_widget(p6_label)

        p6a = FloatLayout()
        p6a_label = Label(text=fourteen, color=(0, 0, 0, 1),size_hint=(1,.2),pos_hint={"top":1,"right":1})
        p6a.add_widget(p6a_label)

        p7 = FloatLayout()
        p7_label = Label(text=fifteen, color=(0, 0, 0, 1),size_hint=(1,.2),pos_hint={"top":1,"right":1})
        p7.add_widget(p7_label)

        p7a = FloatLayout()
        p7a_label = Label(text=sixteen, color=(0, 0, 0, 1),size_hint=(1,.2),pos_hint={"top":1,"right":1})
        p7a.add_widget(p7a_label)

        self.add_widget(title)
        self.add_widget(empty)
        self.add_widget(p1)
        self.add_widget(p1a)
        self.add_widget(p2)
        self.add_widget(p2a)
        self.add_widget(p3)
        self.add_widget(p3a)
        self.add_widget(p4)
        self.add_widget(p4a)
        self.add_widget(p5)
        self.add_widget(p5a)
        self.add_widget(p6)
        self.add_widget(p6a)
        self.add_widget(p7)
        self.add_widget(p7a)