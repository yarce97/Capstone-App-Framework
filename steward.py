#
# Step 1:
#         - Use seed to obtain Steward's DID which already exists on the ledger.
#
#
# Step 2: We use this steward as - a Steward,
#                                - Hospital Trust Anchor, and
#                                - State Trust Anchor
#         In one class, simplifies ceremonial interactions for setting up Trust.
#         This eases background setup that is based on research by Hyperledger Indy.
#         Our research is focused on patient consent
#
#         - add Hospital DID with the role of Trust Anchor to ledger.
#         - Using Steward's DID, a NYM transaction request is built to add the
#           Hospital Trust Anchor's DID and Verkey on the ledger with the role of Trust Anchor.

#         - add State DID with the role of Trust Anchor to ledger.
#         - Using Steward's DID, a NYM transaction request is built to add the
#           State Trust Anchor's DID and Verkey on the ledger with the role of Trust Anchor.
#
# Step3: Credential Setup
#         - Trust Anchors setup schemas.
#         - Trust Anchors setup credential definitions
#

import json
from indy import wallet, pool, ledger, did, anoncreds, crypto, pairwise, non_secrets
from indy.error import IndyError, ErrorCode
from agent import Agent
import pprint
import binascii


class StewardConnectionException(Exception):
    pass


class Steward(Agent):
    '''
    Steward Agent is created as the hospital and state trust anchor
    '''
    def __init__(self, type:str):
        super().__init__(type)
        self.pool_name = 'pool1'
        self.genesis_file = 'C:/Users/yazel/indy-sdk/cli/docker_pool_transactions_genesis'
        self.pool_cfg = None  # {'protocol': protocol_version}
        self.pool_cfg = json.dumps({'genesis_txn': str(self.genesis_file)})
        self.steward_did: str = None
        self.steward_verkey: str = None

        self.state_trust_anchor_did: str = None
        self.state_trust_anchor_verkey: str = None
        self.state_did_for_steward: str = None
        self.medical_schema = None
        self.medical_schema_id: str = None
        self.medical_cred_offer: str = None
        self.medical_cred_def_id: str = None
        self.medical_cred_def_json: str = None

        self.hospG_trust_anchor_did: str = None
        self.hospG_trust_anchor_verkey: str = None
        self.hospG_did_for_steward: str = None
        self.consent_schema = None
        self.consent_schema_id: str = None
        self.consent_cred_offer: str = None
        self.consent_cred_def_id: str = None
        self.consent_cred_def_json: str = None

        self.hospB_trust_anchor_did: str = None
        self.hospB_trust_anchor_verkey: str = None
        self.hospB_did_for_steward: str = None
        self.hospital_schema = None
        self.hospital_schema_id: str = None
        self.hospital_cred_offer: str = None
        self.hospital_cred_def_id: str = None
        self.hospital_cred_def_json: str = None

        self.cred_def_id = None
        self.cred_def_json = None

    def print_steward_log(self, value_color="", value_noncolor=""):
        # set the colors for text. #RED
        HEADER = '\033[91m'
        ENDC = '\033[0m'
        print(HEADER + value_color + ENDC + str(value_noncolor))

    def print_trustanchor_log(self, who='blue', value_color="", value_noncolor=""):
        # set the colors for text.
        if (who=='green'):
            HEADER = '\033[92m'
        elif (who == 'state'):
            HEADER = '\033[93m'
        elif (who == 'blue'):
            HEADER = '\033[94m'
        else:
            HEADER = '\033[95m'
        ENDC = '\033[0m'
        print(HEADER + value_color + ENDC + str(value_noncolor))

    async def generate_and_store_steward_id(self):
        '''
        Generate and store steward ID
        '''
        self.print_steward_log('Steward:generate steward id.\n')

        try:
            self.print_steward_log('Generating and storing steward DID and verkey\n')
            steward_seed = '000000000000000000000000Steward1'
            did_json = json.dumps({'seed': steward_seed})

            self.steward_did, self.steward_verkey = await did.create_and_store_my_did(self.wallet_handle, did_json)
            # By default DID's are generated as the first 16 bytes of the verkey.
            self.print_steward_log('Steward DID: ', self.steward_did)
            self.print_steward_log('Steward Verkey: ', self.steward_verkey)
        except IndyError as e:
            print('Error occurred: %s' % e)

    async def generate_and_store_trustanchor_ids(self):
        '''
        Generate and store trust anchor ID and the hospitals did and verkey
        '''
        self.print_steward_log('Steward:generate trust anchor ids.\n')
        try:
            self.print_steward_log('Generating and storing state trust anchor DID and verkey\n')

            self.state_trust_anchor_did, self.state_trust_anchor_verkey = await did.create_and_store_my_did(self.wallet_handle, "{}")

            self.print_steward_log('State Trust anchor DID: ', self.state_trust_anchor_did)
            self.print_steward_log('State Trust anchor Verkey: ', self.state_trust_anchor_verkey)
        except IndyError as e:
            print('Error occurred: %s' % e)

        try:
            self.print_steward_log('Generating and storing Hospital Blue trust anchor DID and verkey\n')

            self.hospB_trust_anchor_did, self.hospB_trust_anchor_verkey = await did.create_and_store_my_did(self.wallet_handle, "{}")

            self.print_steward_log('Hospital Blue Trust anchor DID: ', self.hospB_trust_anchor_did)
            self.print_steward_log('Hospital Blue Trust anchor Verkey: ', self.hospB_trust_anchor_verkey)
        except IndyError as e:
            print('Error occurred: %s' % e)

        try:
            self.print_steward_log('Generating and storing Hospital Green trust anchor DID and verkey\n')

            self.hospG_trust_anchor_did, self.hospG_trust_anchor_verkey = await did.create_and_store_my_did(self.wallet_handle, "{}")

            self.print_steward_log('Hospital Green Trust anchor DID: ', self.hospG_trust_anchor_did)
            self.print_steward_log('Hospital Green Trust anchor Verkey: ', self.hospG_trust_anchor_verkey)
        except IndyError as e:
            print('Error occurred: %s' % e)

    async def steward_adds_trust_anchors_to_ledger(self):
        '''
        Steward adds trust anchor to ledger
        '''
        self.print_steward_log('Steward: adding Trust Anchor to the ledger.')

        try:
            # STATE as Trust Anchor
            self.print_steward_log('Building NYM request to add *State* Trust Anchor to the ledger\n')
            # This call looks up the private key of the steward DID in our wallet, and uses it to sign the transaction.
            nym_transaction_request = await ledger.build_nym_request(
                self.steward_did,
                self.state_trust_anchor_did,
                self.state_trust_anchor_verkey,
                alias=None,
                role='TRUST_ANCHOR')
            self.print_steward_log('NYM transaction request: ')
            pprint.pprint(json.loads(nym_transaction_request))

            self.print_steward_log('Sending NYM request to the ledger\n')
            nym_transaction_response = await ledger.sign_and_submit_request(self.pool_handle,
                                                                            self.wallet_handle,
                                                                            self.steward_did,
                                                                            nym_transaction_request)
            self.print_steward_log('NYM transaction response for adding STATE as TRUST ANCHOR: ')
            pprint.pprint(json.loads(nym_transaction_response))
            # At this point, we have written a new identity to the ledger.

            # HOSPITAL BLUE as Trust Anchor
            self.print_steward_log('Building NYM request to add *Hospital Blue* Trust Anchor to the ledger\n')
            # This call looks up the private key of the steward DID in our wallet, and uses it to sign the transaction.
            nym_transaction_request = await ledger.build_nym_request(
                self.steward_did,
                self.hospB_trust_anchor_did,
                self.hospB_trust_anchor_verkey,
                alias=None,
                role='TRUST_ANCHOR')
            self.print_steward_log('NYM transaction request: ')
            pprint.pprint(json.loads(nym_transaction_request))

            self.print_steward_log('Sending NYM request to the ledger\n')
            nym_transaction_response = await ledger.sign_and_submit_request(self.pool_handle,
                                                                            self.wallet_handle,
                                                                            self.steward_did,
                                                                            nym_transaction_request)
            self.print_steward_log('NYM transaction response for adding HOSPB as TRUST ANCHOR: ')
            pprint.pprint(json.loads(nym_transaction_response))
            # At this point, we have written a new identity to the ledger.

            # HOSPITAL GREEN as Trust Anchor
            self.print_steward_log('Building NYM request to add *Hospital Green* Trust Anchor to the ledger\n')
            # This call looks up the private key of the steward DID in our wallet,
            # and uses it to sign the transaction.
            nym_transaction_request = await ledger.build_nym_request(
                self.steward_did,
                self.hospG_trust_anchor_did,
                self.hospG_trust_anchor_verkey,
                alias=None,
                role='TRUST_ANCHOR')
            self.print_steward_log('NYM transaction request: ')
            pprint.pprint(json.loads(nym_transaction_request))

            self.print_steward_log('Sending NYM request to the ledger\n')
            nym_transaction_response = await ledger.sign_and_submit_request(self.pool_handle,
                                                                            self.wallet_handle,
                                                                            self.steward_did,
                                                                            nym_transaction_request)
            self.print_steward_log('NYM transaction response for adding HOSPG as TRUST ANCHOR: ')
            pprint.pprint(json.loads(nym_transaction_response))
            # At this point, we have written a new identity to the ledger.
        except IndyError as e:
            print('Error occurred: %s' % e)

    async def steward_generates_credential_offer(self, schematype:str) -> (str, str, str, str):
        '''
        Trust anchor generates credential offer when button is pressed for medical, hospital, or consent
        '''
        # get an initial credential offer when requested.
        try:
            if (schematype == 'medical'):
                self.medical_cred_offer = await anoncreds.issuer_create_credential_offer(
                    self.wallet_handle, self.medical_cred_def_id)
                return (self.medical_cred_def_json,
                        self.medical_cred_def_id,
                        self.medical_cred_offer,
                        json.dumps(self.medical_schema['data']))
            elif (schematype == 'hospital'):
                self.hospital_cred_offer = await anoncreds.issuer_create_credential_offer(
                    self.wallet_handle, self.hospital_cred_def_id)
                return (self.hospital_cred_def_json,
                        self.hospital_cred_def_id,
                        self.hospital_cred_offer,
                        json.dumps(self.hospital_schema['data']))
            elif (schematype == 'consent'):
                self.consent_cred_offer = await anoncreds.issuer_create_credential_offer(
                    self.wallet_handle, self.consent_cred_def_id)
                return (self.consent_cred_def_json,
                        self.consent_cred_def_id,
                        self.consent_cred_offer,
                        json.dumps(self.consent_schema['data']))

            return "", "", ""
        except IndyError as e:
            print('Error occurred: %s' % e)

    # S T A T E   B U I L D S   M E D I C A L   C R E D E N T I A L   S C H E M A
    # SCHEMA ***   S E T U P (schema steps 1-3  of six steps)   **
    async def state_builds_medical_schema(self):
        '''
        medical schema is created
        '''
        generated_schema_request: str = ""
        try:
            self.print_trustanchor_log('state', 'The state, a Trust Anchor, builds the medical credential schema\n')
            seq_no = 1
            self.medical_schema = {
                'seqNo': seq_no,
                'dest': self.steward_did,
                'data': {
                    'id': '1',
                    'name': 'state',
                    'version': '1.0',
                    'ver': '1.0',
                    'attrNames': ['first_name', 'last_name', 'degree', 'level', 'year', 'status']
                }
            }
            schema_data = self.medical_schema['data']
            # Here, build the   R E Q U E S T (schema S T E P: 2)
            generated_schema_request = await ledger.build_schema_request(self.steward_did, json.dumps(schema_data))

            # Here send the REQUEST to the ledger (schema S T E P: 3)
            schema_response = await ledger.sign_and_submit_request(self.pool_handle,
                                                 self.wallet_handle,
                                                 self.steward_did,
                                                 generated_schema_request)
            self.print_trustanchor_log('state', 'Schema response to adding schema to ledger: ')
            pprint.pprint(json.loads(schema_response))
            # PUBLISH The credential to the ledger (covers S T E P S: 4-6)
            # Creating and storing credential definition as trust anchor for the given schema
            cred_def_tag = 'StateMedicalTAG'
            cred_def_type = 'CL'
            cred_def_config = json.dumps({"support_revocation": False})

            (cred_def_id, cred_def_json) = await anoncreds.issuer_create_and_store_credential_def(self.wallet_handle,
                                                                       self.state_trust_anchor_did,
                                                                       json.dumps(schema_data),
                                                                       cred_def_tag,
                                                                       cred_def_type,
                                                                       cred_def_config)
            self.medical_cred_def_id = cred_def_id
            print("1.self.medical_cred_def_id: ")
            pprint.pprint(cred_def_id)

            self.medical_cred_def_json = cred_def_json
            print("2.self.medical_cred_def_json: ")
            pprint.pprint(self.medical_cred_def_json)
        except IndyError as e:
            print('Error occurred: %s' % e)

    # H O S P I T A L   B L U E   B U I L D S   H O S P I T A L   A F F I L I A T I O N   S C H E M A
    # S E T U P (schema steps 1-3 of six steps)
    async def hospital_builds_affiliation_schema(self):
        generated_schema_request: str = ""
        self.print_trustanchor_log('blue', 'Hospital Blue is building affiliation schema.\n')
        try:
            self.print_trustanchor_log('blue', 'Hospital Blue, a Trust Anchor, builds the affiliation credential schema\n')
            seq_no = 1
            self.hospital_schema = {
                'seqNo': seq_no,
                'dest': self.steward_did,
                'data': {
                    'name': 'MedICMedicalAffiliations',
                    'version': '1.0',
                    'ver': '1.0',
                    'attrNames': ['hospital','first_name','last_name','start_date', 'end-date', 'status']
                }
            }
            schema_data = self.hospital_schema['data']

            # Here, build the   R E Q U E S T (schema S T E P: 2)
            generated_schema_request = await ledger.build_schema_request(self.steward_did, json.dumps(schema_data))

            # Here send the REQUEST to the ledger (schema S T E P: 3)
            schema_response = await ledger.sign_and_submit_request(self.pool_handle,
                                                 self.wallet_handle,
                                                 self.steward_did,
                                                 generated_schema_request)

            self.print_trustanchor_log('blue', 'Schema response to adding schema to ledger: ')
            pprint.pprint(json.loads(schema_response))
            cred_def_tag = 'StateHospitalTAG'
            cred_def_type = 'CL'
            cred_def_config = json.dumps({"support_revocation": False})
            (cred_def_id, cred_def_json) = await anoncreds.issuer_create_and_store_credential_def(self.wallet_handle,
                                                                       self.hospB_trust_anchor_did,
                                                                       json.dumps(schema_data),
                                                                       cred_def_tag,
                                                                       cred_def_type,
                                                                       cred_def_config)
            self.hospital_cred_def_id = cred_def_id
            self.hospital_cred_def_json = cred_def_json
        except IndyError as e:
            print('Error occurred: %s' % e)

    # H O S P I T A L   G R E E N   B U I L D S   C O N S E N T   S C H E M A
    # SCHEMA ***   S E T U P (schema steps 1-3  of six steps)
    async def hospital_builds_patient_consent(self):
        generated_schema_request: str = ""
        self.print_trustanchor_log('hospG', 'Building patient consent schema.\n')
        try:
            self.print_trustanchor_log('green', 'Hospital Green, a Trust Anchor, builds the medical credential schema\n')
            seq_no = 2
            self.consent_schema = {
                'seqNo': seq_no,
                'dest': self.steward_did,
                'data': {
                    'id': '2',
                    'name': 'MedICMedicalConsent',
                    'version': '1.0',
                    'ver': '1.0',
                    'attrNames': ["first_name", "last_name", "first_date", "end_date",
                                  "hospital", "credential_requirement", "hospital_affiliation",
                                  "pace_functionality", "defib_functionality"]
                    }
            }
            schema_data = self.consent_schema['data']

            # Here, build the   R E Q U E S T (schema S T E P: 2)
            generated_schema_request = await ledger.build_schema_request(self.steward_did, json.dumps(schema_data))

            # Here send the REQUEST to the ledger (schema S T E P: 3)
            schema_response = await ledger.sign_and_submit_request(self.pool_handle,
                                                 self.wallet_handle,
                                                 self.steward_did,
                                                 generated_schema_request)

            self.print_trustanchor_log('green', 'Schema response to adding schema to ledger: ')
            pprint.pprint(json.loads(schema_response))

            cred_def_tag = 'StateConsentTAG'
            cred_def_type = 'CL'
            cred_def_config = json.dumps({"support_revocation": False})

            (cred_def_id, cred_def_json) = await anoncreds.issuer_create_and_store_credential_def(self.wallet_handle,
                                                                       self.hospG_trust_anchor_did,
                                                                       json.dumps(schema_data),
                                                                       cred_def_tag,
                                                                       cred_def_type,
                                                                       cred_def_config)
            self.consent_cred_def_id = cred_def_id
            self.consent_cred_def_json = cred_def_json
        except IndyError as e:
            print('Error occurred: %s' % e)

    # =====================   Proving credential S T U F F    ========================

    async def create_medical_credential(self, my_did, cred_def_id, cred_offer, cred_request) -> str:
        '''
        The medical credential is created
        '''
        print("STEWARD TESTING: encoding")
        pprint.pprint(str("Bob".encode('UTF-8')))
        teststr: str = "Bob"
        testvalue: int = teststr.encode('UTF-8')
        testintvalue = int(binascii.hexlify("Bob".encode('utf-8')),16)
        pprint.pprint(testvalue)
        pprint.pprint(str(testvalue))
        pprint.pprint(str(testintvalue))

        print('Trust_anchor is creating a credential offer for Bob.\n')

        cred_values: str = json.dumps({
                "first_name": {"raw": "Bob", "encoded": str(int(binascii.hexlify("Bob".encode('utf-8')), 16))},
                "last_name": {"raw": "Smith", "encoded": str(int(binascii.hexlify("Smith".encode('utf-8')), 16))},
                "degree":  {"raw": "Doctor", "encoded": str(int(binascii.hexlify("Nurse".encode('utf-8')), 16))},
                "level":   {"raw": "Heart",  "encoded": str(int(binascii.hexlify("Heart".encode('utf-8')), 16))},
                "year":    {"raw": "2015",   "encoded": "2015"},
                "status":  {"raw": "Good",   "encoded": str(int(binascii.hexlify("Good".encode('utf-8')), 16))} })

        generated_cred, _, _ = await anoncreds.issuer_create_credential(
            self.wallet_handle,
            cred_offer,
            cred_request,
            cred_values,
            None, None)
        return generated_cred

    async def create_consent_credential(self, my_did, cred_def_id, cred_offer, cred_request) -> str:
        '''
        Consent credential is created.
        '''
        print('Trust_anchor is creating a consent credential offer for Alice.\n')

        cred_values: str = json.dumps({
                "first_name":         {"raw": "Alice", "encoded":
                    str(int(binascii.hexlify( "Alice".encode('utf-8')),16)) },
                "last_name":          {"raw": "Garcia", "encoded":
                    str(int(binascii.hexlify( "Garcia".encode('utf-8')),16)) },
                "first_date":         {"raw": "20180901", "encoded":
                    str(int(binascii.hexlify( "20180901".encode('utf-8')), 16))},
                "end_date":           {"raw": "20200901", "encoded":
                    str(int(binascii.hexlify( "20200901".encode('utf-8')), 16))},
                "hospital":           {"raw": "Hospital Green", "encoded":
                    str(int(binascii.hexlify( "Hospital Green".encode('utf-8')),16)) },
                "credential_requirement": {"raw": "Doctor",  "encoded":
                    str(int(binascii.hexlify( "Doctor".encode('utf-8')),16)) },
                "hospital_affiliation": {"raw": "True",   "encoded":
                    str(int(binascii.hexlify( "True".encode('utf-8')),16)) },
                "pace_functionality": {"raw": "True", "encoded":
                    str(int(binascii.hexlify( "True".encode('utf-8')), 16))},
                "defib_functionality": {"raw": "False", "encoded":
                    str(int(binascii.hexlify("False".encode('utf-8')), 16))}
        })

        generated_cred, _, _ = await anoncreds.issuer_create_credential(
            self.wallet_handle,
            cred_offer,
            cred_request,
            cred_values,
            None, None)

        return generated_cred
