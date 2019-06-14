""" Module to handle the connection process.
"""

# pylint: disable=import-error

import json
import base64
from indy import crypto, did, pairwise, non_secrets, error, anoncreds
from indy.error import IndyError, ErrorCode
import serializer.json_serializer as Serializer
from message import Message
from pprint import pprint


class BadInviteException(Exception):
    def __init__(self, msg):
        super().__init__(msg)


class Credential:
    # Message Types
    CREDENTIAL_OFFER_GENERATE = "generate_credential_offer"
    CREDENTIAL_OFFER = "credential_offer"
    CREDENTIAL_OFFER_RECEIVED = "credential_offer_received"
    CREDENTIAL_REQUEST = "credential_request"
    CREDENTIAL_REQUEST_RECEIVED = "credential_request_received"
    CREDENTIAL = "credential"
    CREDENTIAL_OBTAINED = "credential_obtained"
    CREDENTIAL_ACK = "credential_ack"
    CREDENTIAL_ACK_RECEIVED = "credential_ack_received"

    def __init__(self, agent):
        self.agent = agent

    async def generate_credential_offer(self, schematype, their_did, my_did, name_send):
        '''
        The steward sends a credential offer to the prover,
        generating credentials will be done by hospitals and state only, not patients
        '''
        print("\n\nGENERATE CREDENTIAL OFFER\n\n")
        if (self.agent.type == 'State'):
            print("+++ CREDENTIAL: received view request to generate a credential offer.")
            (cred_def, cred_def_id, cred_offer, issuer_schema) = await self.agent.steward_generates_credential_offer(schematype)
            print("Credential: steward created cred_def: ")
            pprint(cred_def)
            print("Credential: steward created cred_def_id: ")
            pprint(cred_def_id)
            print("Credential: steward created cred_offer: ")
            pprint(cred_offer)

            offer_msg = Message({
                '@type': Credential.CREDENTIAL_OFFER,
                '@sendTo': name_send,
                '@from': self.agent.owner,
                'data': {
                    'their_did': their_did,
                    'my_did': my_did,
                    'schematype': schematype,
                    'issuer_schema': issuer_schema,
                    'cred_def_id': cred_def_id,
                    'cred_offer': cred_offer,
                    'cred_def': cred_def,
                    'nonce': 123456,
                    'signature': 123}
            })

            # Sign it with your own key - you have given the verkey to other end already
            verkey = await did.key_for_did(self.agent.pool_handle,
                                           self.agent.wallet_handle,
                                           my_did)

            offer_msg['signature'] = await self.agent.sign_agent_message_field(
                offer_msg['data'], verkey)

            print("+++ CREDENTIAL: sending credential offer.")
            pprint(offer_msg)
            await self.agent.send_message_to_agent(their_did, offer_msg)

    async def credential_offer(self, msg: Message) -> Message:
        '''
        Prover receives credential offer from trust anchor, therefore the credential-request
        will be sent to request credential
        '''
        print("\n\n CREDENTIAL OFFER\n\n")
        data = msg['data']
        their_did = data['my_did']  # this message comes from other agent
        my_did = data['their_did']  # this message comes from other agent
        nonce: int = data['nonce']
        schematype = data['schematype']

        sendTo = msg['@from']
        from_ = msg['@sendTo']
        print("SEND TO: ", sendTo, "   From: ", from_)

        cred_def = data['cred_def']
        cred_def_id = data['cred_def_id']
        cred_offer = data['cred_offer']

        if (schematype == 'medical'):
            self.agent.medical_cred_offer = cred_offer
            self.agent.medical_cred_def_id = cred_def_id
            self.agent.medical_cred_def = cred_def
            self.agent.medical_schema = data['issuer_schema']
        elif (schematype == 'consent'):
            self.agent.consent_cred_offer = cred_offer
            self.agent.consent_cred_def_id = cred_def_id
            self.agent.consent_cred_def = cred_def
            self.agent.consent_schema = data['issuer_schema']
        elif (schematype == 'hospital'):
            self.agent.hospital_cred_offer = cred_offer
            self.agent.hospital_cred_def_id = cred_def_id
            self.agent.hospital_cred_def = cred_def
            self.agent.hospital_schema = data['issuer_schema']

        print("+++ CREDENTIAL: prover received a credential offer.")
        print("Going to send a credential request.")
        pprint(msg.as_json())

        my_cred_request, my_request_metadata = await self.agent.prepare_credential_request(cred_def,
                                                        cred_offer,
                                                        my_did,
                                                        their_did)
        request_msg = Message({
            '@type': Credential.CREDENTIAL_REQUEST,
            '@sendTo': sendTo,
            "@from": from_,
            'data': {
                'their_did': their_did,
                'my_did': my_did,
                'schematype': schematype,
                'cred_def_id': cred_def_id,
                'cred_def': cred_def,
                'cred_request': my_cred_request,
                'cred_request_meta': my_request_metadata,
                'cred_offer': cred_offer,
                'nonce': str(int(nonce) + 1),
                'signature': 123
            }
        })
        pairwise_info = json.loads(await pairwise.get_pairwise(
                                            self.agent.wallet_handle,
                                            their_did))
        pairwise_meta = json.loads(pairwise_info['metadata'])
        print("+++ CREDENTIAL: sending a CREDENTIAL REQUEST:")
        pprint(request_msg)
        print("CREDENTIAL: signing message field.")
        print("CREDENTIAL: pairwisemeta[connection key]: " + pairwise_meta['connection_key'])
        verkey = await did.key_for_did(self.agent.pool_handle,
                                       self.agent.wallet_handle, my_did)
        request_msg['signature'] = await self.agent.sign_agent_message_field(
            request_msg['data'], verkey)
        # message is sent to other agent
        await self.agent.send_message_to_agent(their_did, request_msg)
        print("+++ CREDENTIAL: sending a CREDENTIAL REQUEST")
        pprint(request_msg)

    async def credential_request(self, msg: Message) -> Message:
        '''
        Issuer receives request for a credential, and the issuer gets ready to send it it to the prover.
        '''
        print("\n\n CREDENTIAL REQUEST\n\n")

        data = msg['data']
        schematype = data['schematype']
        nonce = data['nonce']
        their_did = data['my_did']  # this message comes from other agent
        my_did = data['their_did']  # this message comes form other agent

        cred_def_id = data['cred_def_id']
        cred_offer = data['cred_offer']
        cred_request = data['cred_request']

        sendTo = msg['@from']
        from_ = msg['@sendTo']

        print("+++ CREDENTIAL: received a CREDENTIAL REQUEST.")
        pprint(msg.as_json())

        generated_cred: str = ""
        if (schematype == 'medical'):
            their_cred_def = self.agent.medical_cred_def_id
            generated_cred = await self.agent.create_medical_credential(my_did, cred_def_id,
                                                                        cred_offer, cred_request)
        elif (schematype == 'consent'):
            their_cred_def = self.agent.consent_cred_def_id
            generated_cred = await self.agent.create_consent_credential(my_did, cred_def_id,
                                                                        cred_offer, cred_request)
        elif (schematype == 'hospital'):
            their_cred_def = self.agent.hospital_cred_def_id
            generated_cred = await self.agent.create_hospital_credential(my_did, cred_def_id,
                                                                        cred_offer, cred_request)

        cred_msg = Message({
            '@type': Credential.CREDENTIAL,
            '@sendTo': sendTo,
            '@from': from_,
            'data': {
                'their_did': their_did,
                'my_did': my_did,
                'schematype': schematype,
                'cred': generated_cred,
                'cred_offer': cred_offer,
                'cred_def_id': cred_def_id,
                'cred_request': cred_request,
                'cred_request_meta': data['cred_request_meta'],
                'cred_def': data['cred_def'],
                'nonce': str(int(nonce)+1),
                'signature': 123
            }
        })
        verkey = await did.key_for_did(self.agent.pool_handle, self.agent.wallet_handle, my_did)
        cred_msg['signature'] = await self.agent.sign_agent_message_field(
            cred_msg['data'], verkey)
        # send msg to other user
        await self.agent.send_message_to_agent(their_did, cred_msg)

        print("+++ CREDENTIAL: sending a CREDENTIAL.")
        pprint(cred_msg)

    async def credential_received(self, msg: Message) -> Message:
        '''
        Prover receives the credential
        '''
        print("\n\n CREDENTIAL RECIEVED\n\n")
        data = msg['data']
        schematype = data['schematype']
        nonce = data['nonce']
        their_did = data['my_did']  # this message comes from other agent
        my_did = data['their_did']  # this message comes form other agent

        await anoncreds.prover_store_credential(self.agent.wallet_handle,
                                                None,
                                                data['cred_request_meta'],
                                                data['cred'],
                                                data['cred_def'],
                                                None
                                                )
        if (schematype == 'medical'):
            self.agent.medical_cred_def_id = data['cred_def_id']
            self.agent.medical_cred_offer = data['cred_offer']
            self.agent.got_medical_credential = True

        if (schematype == 'consent'):
            self.agent.got_consent_credential = True

        print("+++ Credential prover stores credential: their did: " + their_did)
        print("Credential: got credential. Sending to view." + self.agent.owner)

        credential_msg = Message({
            '@type': Credential.CREDENTIAL_OBTAINED,
            'label': self.agent.owner,
            'schematype': schematype,
            'data': data['cred']
        })

        b64_cred = \
            base64.urlsafe_b64encode(bytes(Serializer.pack(credential_msg), 'utf-8')).decode('ascii')

        print("CREDENTIAL: done storing credential")

    async def verify_cred_offer(self, their_did: str, schema_id: str):
        print("AGENT: This is the credential offer that we received!!!")

    async def prepare_credential_request(self, cred_def: str, cred_offer: str, my_did: str, their_did: str) -> (str, str):
        master_secret: str = ""
        generated_cred_def_request: str = ""
        generated_cred_def_response: str = ""

        try:
            secret_name = 'secret'   # secret put in wallet, this is just the name
            self.master_secret = await anoncreds.prover_create_master_secret(self.wallet_handle, secret_name)
            print("Agent: Got master key in wallet. Preparing to blind it and send to Issuer.")

            my_cred_request, cred_request_metadata = await anoncreds.prover_create_credential_req(
                self.wallet_handle,
                cred_offer,
                cred_def,
                secret_name)

            print("Agent: my_cred_request: ", my_cred_request)
            print("Agent: my_cred_request_metadata: ", cred_request_metadata)

            return my_cred_request, cred_request_metadata
        except IndyError as e:
            print('Error occurred: %s' % e)
