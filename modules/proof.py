""" Module to handle the connection process.
"""

# pylint: disable=import-error

import json
import base64
from indy import crypto, did, pairwise, non_secrets, error, anoncreds
import serializer.json_serializer as Serializer
from message import Message
from pprint import pprint


class BadInviteException(Exception):
    def __init__(self, msg):
        super().__init__(msg)


class Proof:
    # Message Types
    PROOF_OFFER_GENERATE = "generate_proof_offer"
    PROOF_OFFER = "proof_offer"
    PROOF_OFFER_RECEIVED = "proof_offer_received"
    TRUST_ANCHOR_SET = "trust_anchor_set"
    PROOF_REQUEST = "proof_request"
    PROOF = "proof"
    PROOF_RECEIVED = "proof_received"
    PROOF_ACK = "proof_ack"

    def __init__(self, agent):
        self.agent = agent

    # The following function is called when there is a trigger received from UI.
    # The UI is triggering the medical personnel to sent a proof offer to the patient.
    async def generate_proof_offer(self, their_did, my_did, sendTo, from_):
        '''
        Trigger for medical professional to sent proof offer to patient
        '''
        print("\n\nGENERATE PROOF OFFER\n\n")
        # generating proofs will be done by hospitals and state only, not patients
        if self.agent.type != 'State':
            nonce = self.agent.proof_nonce

            self.agent.their_did_cred_offer = their_did
            self.agent.my_did_cred_offer = my_did
            print("+++ PROOF: received view request to generate a proof offer.")

            offer_msg = Message({
                '@type': Proof.PROOF_OFFER,
                '@sendTo': sendTo,
                '@from': from_,
                'data': {
                    'their_did': their_did,
                    'my_did': my_did,
                    'nonce': nonce
                }
            })
            await self.agent.send_message_to_agent(their_did, offer_msg)

    # the patient has received a proof offer. They need to set the DID for the
    # trusted party. Send a message to the UI to get the trusted DID
    async def proof_offer(self, msg: Message) -> Message:
        '''
        Patient receives proof offer, the DID needs to be set for the trusted party.
        '''
        print("\n\n PROOF OFFER\n\n")
        data = msg['data']
        their_did = data['my_did']  # this message comes from other agent
        my_did = data['their_did']  # this message comes from other agent
        nonce: int = data['nonce']
        from_ = msg['@sendTo']
        sendTo = msg['@from']

        self.agent.their_did_cred_offer = their_did
        self.agent.my_did_cred_offer = my_did
        self.agent.proof_nonce = nonce

        print("+++ PROOF: prover received a proof offer.")
        pprint(msg.as_json())
        # get hospital and state TA and send
        await self.proof_offer_send(
            Message({
                '@type': Proof.PROOF_OFFER_RECEIVED,
                '@sendTo': sendTo,
                '@from': from_,
                'data': {
                    'their_did': their_did
                }
            })
        )

    async def proof_offer_send(self, msg: Message) -> Message:
        '''
        Proof request will be sent by patient to request a proof
        '''
        print("\n\n PROOF OFFER SEND\n\n")
        data = msg['message']
        their_did = self.agent.their_did_cred_offer
        my_did = self.agent.my_did_cred_offer
        sendTo = msg['@sendTo']
        from_ = msg['@from']

        print("Received the proof offer. Here is the trust_anchor_did:")
        pprint(self.agent.State_TA_DID)
        print("+++ PROOF: Going to send a proof request.")
        pprint(msg.as_json())
        nonce = self.agent.proof_nonce + 1

        consent_proof_request_json = {
            'nonce': str(nonce),
            'name': 'Consent-Request',
            'version': '0.1',
            'requested_attributes': {
                'attr1_referent': {
                    'name': 'first_name',
                    "restrictions": {
                        "issuer_did": self.agent.State_TA_DID
                    }
                },
                'attr2_referent': {
                    'name': 'degree',
                    "restrictions": {
                        "issuer_did": self.agent.State_TA_DID
                    }
                },
                'attr3_referent': {
                    'name': 'status',
                    "restrictions": {
                        "issuer_did": self.agent.State_TA_DID
                    }
                }
            },
            'requested_predicates': {}
        }
        consent_proof_request = json.dumps(consent_proof_request_json)

        request_msg = Message({
            '@type': Proof.PROOF_REQUEST,
            '@sendTo': sendTo,
            '@from': from_,
            'data': {
                'their_did': their_did,
                'my_did': my_did,
                'proof_request': consent_proof_request,
                'nonce': str(int(nonce) + 1),
                'signature': 123
            }
        })

        pairwise_info = json.loads(await pairwise.get_pairwise(self.agent.wallet_handle, their_did))
        pairwise_meta = json.loads(pairwise_info['metadata'])

        await self.agent.send_message_to_agent(their_did, request_msg)

    async def proof_request(self, msg: Message) -> Message:
        '''
        The medical personnel receives a request for a proof.
        '''
        print("\n\n PROOF REQUEST\n\n")
        data = msg['data']
        nonce = data['nonce']
        their_did = data['my_did']  # this message comes from other agent
        my_did = data['their_did']  # this message comes form other agent
        sendTo = msg['@from']
        from_ = msg['@sendTo']
        consent_proof_request = data['proof_request']

        # Prover creates Proof for Proof request
        prover_cred_search_handle = await anoncreds.prover_search_credentials_for_proof_req(
            self.agent.wallet_handle, consent_proof_request, None)

        creds_for_attr1 = await anoncreds.prover_fetch_credentials_for_proof_req(
            prover_cred_search_handle, 'attr1_referent', 1)
        prover_cred_for_attr1 = json.loads(creds_for_attr1)[0]['cred_info']
        print("Prover credential for attr1_referent: ")
        pprint(prover_cred_for_attr1)

        creds_for_attr2 = await anoncreds.prover_fetch_credentials_for_proof_req(
            prover_cred_search_handle, 'attr2_referent', 1)
        prover_cred_for_attr2 = json.loads(creds_for_attr2)[0]['cred_info']
        print("Prover credential for attr2_referent: ")
        pprint(prover_cred_for_attr2)

        creds_for_attr3 = await anoncreds.prover_fetch_credentials_for_proof_req(
            prover_cred_search_handle, 'attr3_referent', 1)
        prover_cred_for_attr3 = json.loads(creds_for_attr3)[0]['cred_info']
        print("Prover credential for attr3_referent: ")
        pprint(prover_cred_for_attr3)

        await anoncreds.prover_close_credentials_search_for_proof_req(prover_cred_search_handle)

        print("Prover creates Proof for Proof Request")
        prover_requested_creds = json.dumps({
            'self_attested_attributes': {},
            'requested_attributes': {
                'attr1_referent': {
                    'cred_id': prover_cred_for_attr1['referent'],
                    'revealed': True
                },
                'attr2_referent': {
                    'cred_id': prover_cred_for_attr2['referent'],
                    'revealed': True
                },
                'attr3_referent': {
                    'cred_id': prover_cred_for_attr1['referent'],
                    'revealed': True
                }
            },
            'requested_predicates': {}
        })
        print("Requested Credentials for Proving ")
        pprint(json.loads(prover_requested_creds))

        # get the credential schema and corresponding credential definition for each used credential
        cred_offer = json.loads(self.agent.medical_cred_offer)
        prover_schema_id_json = json.loads(cred_offer['schema_id'])
        schemas = json.dumps({prover_schema_id_json: json.loads(self.agent.medical_schema)})

        cred_defs = json.dumps({self.agent.medical_cred_def_id: json.loads(self.agent.medical_cred_def)})
        consent_proof = await anoncreds.prover_create_proof(self.agent.wallet_handle,
                                                            consent_proof_request,
                                                            prover_requested_creds,
                                                            self.agent.master_secret,
                                                            schemas,
                                                            cred_defs,
                                                            "{}"
                                                            )

        print("+++ PROOF: sending the proof.")
        pprint(consent_proof)

        cred_msg = Message({
            '@type': Proof.PROOF,
            '@sendTo': sendTo,
            '@from': from_,
            'data': {
                'their_did': their_did,
                'my_did': my_did,
                'consent_proof_request': consent_proof_request,
                'consent_proof': consent_proof,
                'schemas': schemas,
                'cred_defs': cred_defs,
                'nonce': str(int(nonce) + 1),
                'signature': 123
            }
        })
        verkey = await did.key_for_did(self.agent.pool_handle, self.agent.wallet_handle, my_did)
        cred_msg['signature'] = await self.agent.sign_agent_message_field(
            cred_msg['data'], verkey)
        await self.agent.send_message_to_agent(their_did, cred_msg)

        print("+++ PROOF: sending a PROOF.")
        pprint(cred_msg)

    async def proof_received(self, msg: Message) -> Message:
        print("\n\n PROOF RECIEVED\n\n")
        data = msg['data']
        nonce = data['nonce']
        their_did = data['my_did']  # this message comes from other agent
        my_did = data['their_did']  # this message comes form other agent

        proof = data['consent_proof']
        consent_proof_request = data['consent_proof_request']
        schemas = data['schemas']
        cred_defs = data['cred_defs']

        print("Verifier is verifying proof from Prover\n")
        assert await anoncreds.verifier_verify_proof(consent_proof_request,
                                                     proof,
                                                     schemas,
                                                     cred_defs,
                                                     "{}", "{}")

        print("+++ PROOF prover stores proof: their did: " + their_did)
        print("Credential: got proof. Sending to view." + self.agent.owner)

        proof_msg = Message({
            '@type': Proof.PROOF,
            'label': self.agent.owner,
            'cred': proof
        })

        b64_cred = base64.urlsafe_b64encode(bytes(Serializer.pack(
                proof_msg), 'utf-8')).decode('ascii')

        print("PROOF: done storing proof")
