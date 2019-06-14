import json
import base64
import asyncio
import time
import struct
import socket_client
from indy import wallet, did, error, crypto, pairwise, pool, anoncreds
from indy_sdk_utils import get_wallet_records
from message import Message
import serializer.json_serializer as Serializer
import indy_sdk_utils as utils
from indy.error import IndyError


class WalletConnectionException(Exception):
    pass


class Agent:
    '''
    Creates an Agent that is either a patient, doctor, or agency
    '''
    def __init__(self, type:str):
        self.type:str = type    # patient, doctor, agency
        self.pool_name = 'pool2'
        self.genesis_file = 'C:/Users/yazel/indy-sdk/cli/docker_pool_transactions_genesis'
        self.pool_cfg = json.dumps({'genesis_txn': str(self.genesis_file)})
        self.pool_handle = None

        self.owner = None
        self.wallet_handle = None
        self.endpoint_vk = None
        self.initialized = False
        self.invitations = None
        self.pairwise_connections = None
        self.message_queue = asyncio.Queue()
        self.outbound_admin_message_queue = asyncio.Queue()
        self.modules = {}

        self.master_secret = None
        self.got_medical_credential = False
        self.medical_cred_def_id = None
        self.medical_cred_offer = None
        self.medical_schema = None
        self.medical_cred_def = None

        self.got_consent_credential = False
        self.consent_cred_def_id = None
        self.consent_cred_offer = None
        self.consent_schema = None
        self.consent_cred_def = None

        self.State_TA_DID = None
        self.Hospital_TA_DID = None
        self.their_did_cred_offer = None
        self.proof_nonce = 87392
        self.my_did_cred_offer = None

    # create wallet if wallet with agent_name does not exist, otherwise verify passphase is the same
    async def connect_wallet(self, agent_name, passphrase):
        '''
        Creates wallet if wallet with agent names does not exist, otherwise it verifies if the passphrase
        matches wallet with existing wallet passphrase
        :param agent_name: name of wallet
        :param passphrase: password
        '''
        walletExists = False
        passwordWrong = False
        self.owner = agent_name
        wallet_suffix = "wallet"
        wallet_name = '{}-{}'.format(self.owner, wallet_suffix)
        wallet_config = json.dumps({"id": wallet_name})
        wallet_credentials = json.dumps({"key": passphrase})

        # create wallet
        try:
            await wallet.create_wallet(wallet_config, wallet_credentials)
        except error.IndyError as e:
            if e.error_code is error.ErrorCode.WalletAlreadyExistsError:
                walletExists = True         # wallet already exisits
            else:
                print("Unexpected Indy Error: {}".format(e))
        except Exception as e:
            print("Other Error: ", e)

        # open wallet
        try:
            self.wallet_handle = await wallet.open_wallet(wallet_config, wallet_credentials)
            _, self.endpoint_vk = await did.create_and_store_my_did(self.wallet_handle, "{}")
            self.initialized = True
        except error.IndyError as e:
            if e.error_code is error.ErrorCode.WalletAccessFailed:
                passwordWrong = True    # wallet exists and password is incorrect
        except Exception as e:
            print(e)
            print("Could not open wallet!")
        # if wallet already exists and password is incorrect
        if walletExists and passwordWrong:
            return False
        else:
            return True

    async def get_agent_name(self):
        '''
        :return: name if the agent
        '''
        return self.owner

    def get_med_cred(self):
        '''
        :return: medical credentials for patient
        '''
        return self.got_medical_credential

    def get_consent_cred(self):
        '''
        :return: consent credentials for patient
        '''
        return self.got_consent_credential

    async def get_pairwise_connections(self):
        '''
        Get the connections that already exist for that user.
        '''
        if self.initialized:
            self.pairwise_connections = []
            agent_pairwises_list_str = await pairwise.list_pairwise(self.wallet_handle)
            agent_pairwises_list = json.loads(agent_pairwises_list_str)         # list of connections
            for agent_pairwise_str in agent_pairwises_list:
                pairwise_record = json.loads(agent_pairwise_str)
                pairwise_record['metadata'] = json.loads(pairwise_record['metadata'])
                self.pairwise_connections.append(pairwise_record)
            return self.pairwise_connections
        else:
            return None

    async def get_invitations(self):
        """
        retrieve list of records of invitations
        """
        if self.initialized:
            self.invitations = await get_wallet_records(self.wallet_handle, "invitations")     # get the records of invitations
            print("INVITATIONS: ", self.invitations)
            return self.invitations
        else:
            return None

    async def sign_agent_message_field(self, field_value, my_vk):
        '''
        Signature is created that contains the vk, a timestamp, and the signature
        '''
        print("sign agent message", field_value)
        timestamp_bytes = struct.pack(">Q", int(time.time()))

        sig_data_bytes = timestamp_bytes + json.dumps(field_value).encode('ascii')
        print(sig_data_bytes)
        sig_data = base64.urlsafe_b64encode(sig_data_bytes).decode('ascii')

        signature_bytes = await crypto.crypto_sign(
            self.wallet_handle,
            my_vk,
            sig_data_bytes
        )
        signature = base64.urlsafe_b64encode(
            signature_bytes
        ).decode('ascii')
        print("signature: ", signature)

        return {
            "@type": "SIGNATURE",
            "signer": my_vk,
            "sig_data": sig_data,
            "signature": signature
        }

    async def unpack_and_verify_signed_agent_message_field(self, signed_field):
        '''
        signature is unpacked that data is returned and verified
        '''
        print("\nagent unpack and verify")
        signature_bytes = base64.urlsafe_b64decode(signed_field['signature'].encode('ascii'))
        sig_data_bytes = base64.urlsafe_b64decode(signed_field['sig_data'].encode('ascii'))
        sig_verified = await crypto.crypto_verify(
            signed_field['signer'],
            sig_data_bytes,
            signature_bytes
        )
        data_bytes = base64.urlsafe_b64decode(signed_field['sig_data'])
        timestamp = struct.unpack(">Q", data_bytes[:8])
        fieldjson = data_bytes[8:]
        return json.loads(fieldjson), sig_verified

    async def unpack_agent_message(self, wire_msg_bytes):
        '''
        Message passed is unpacked as bytes and returned
        '''
        print("\nUnpack agent message")
        if isinstance(wire_msg_bytes, str):
            wire_msg_bytes = bytes(wire_msg_bytes, 'utf-8')
        unpacked = json.loads(
            await crypto.unpack_message(
                self.wallet_handle,
                bytes(wire_msg_bytes)
            )
        )
        print("UNPACKED: ", unpacked)

        from_key = None
        from_did = None
        if 'sender_verkey' in unpacked:
            from_key = unpacked['sender_verkey']
            from_did = await utils.did_for_key(self.wallet_handle, unpacked['sender_verkey'])

        to_key = unpacked['recipient_verkey']
        to_did = await utils.did_for_key(self.wallet_handle, unpacked['recipient_verkey'])

        msg = Serializer.unpack(unpacked['message'])
        print(msg)

        msg.context = {
            'from_did': from_did, # Could be None
            'to_did': to_did, # Could be None
            'from_key': from_key, # Could be None
            'to_key': to_key
        }
        print("Message context: ", msg.context)
        return msg

    async def send_message_to_agent(self, to_did, msg:Message):
        '''
        Pairwise information is retrieved and message is sent to user
        '''
        print("\nSending message to agent:", msg)
        their_did = to_did

        pairwise_info = json.loads(await pairwise.get_pairwise(self.wallet_handle, their_did))
        pairwise_meta = json.loads(pairwise_info['metadata'])

        my_did = pairwise_info['my_did']
        their_vk = pairwise_meta['their_vk']
        my_vk = await did.key_for_local_did(self.wallet_handle, my_did)

        await self.send_message_to_endpoint_and_key(my_vk, their_vk, msg)

    async def send_message_to_endpoint_and_key(self, my_ver_key, their_ver_key, msg):
        '''
        Message is encrypted and sent to the other user through the server
        '''
        print("\nSend message to end and key")
        print(my_ver_key, their_ver_key, msg)

        wire_message = await crypto.pack_message(
            self.wallet_handle,
            Serializer.pack(msg),
            [their_ver_key],
            my_ver_key
        )
        print("wire:", wire_message)
        socket_client.send(wire_message)
        print("SEND MESSAGE")

    async def read_msg(self, wire_msg):
        '''
        Message is unpacked depending on how its encrypted and returned unpacked
        '''
        print("read wire msg: ", wire_msg)
        msg = ""
        try:
            msg = Serializer.unpack(wire_msg)
        except Exception as e:
            print("Message encrypted, trying to unpack", e)

        if not isinstance(msg, Message) or "@type" not in msg:
            try:
                msg = await self.unpack_agent_message(wire_msg)
                print("msg unpack: ", msg)
                return msg
            except Exception as e:
                print("Failed to unpack messgae", e)

    async def delete_wallet(self, agent_name, passphrase):
        '''
        Wallet is deleted from the records depending on the wallet name and passphrase entered
        '''
        deleted = False
        self.owner = agent_name
        wallet_suffix = "wallet"
        wallet_name = '{}-{}'.format(self.owner, wallet_suffix)
        wallet_config = json.dumps({"id": wallet_name})
        wallet_credentials = json.dumps({"key": passphrase})

        try:
            await wallet.close_wallet(self.wallet_handle)       # wallet is closed
            deleted = True
        except error.IndyError as e:
            print("Unexpected error: {}".format(e))
            deleted = False
        except Exception as e:
            print(e)
            deleted = False
        try:
            await wallet.delete_wallet(wallet_config, wallet_credentials)       # wallet is deleted
            print("Remove wallet")
            deleted = True
        except error.IndyError as e:
            if e.error_code is error.ErrorCode.WalletNotFoundError:
                pass
            else:
                print("UNexpected Indy Error: {}".format(e))
            deleted = False
        except Exception as e:
            print(e)
            deleted = False
        return deleted

    async def connect_to_pool(self):
        '''
        Connection to the pool is generated and opened. If the pool exists, it's deleted and created again
        '''
        connected = False
        print("AGENT: CONNECT TO POOL")
        print("AGRNT CREATE NEW POOL LEDGER CONFIG TO LEDGER")
        self.pool_name = self.pool_name + self.owner

        try:
            await pool.set_protocol_version(2)
            await pool.create_pool_ledger_config(self.pool_name, self.pool_cfg)
            connected = True
        except error.IndyError as e:
            if e.error_code == error.ErrorCode.PoolLedgerConfigAlreadyExistsError:
                print("AGENT POOL LEDGER CONFIG ALREADY EXIST")
                await pool.delete_pool_ledger_config(self.pool_name)
                await pool.create_pool_ledger_config(self.pool_name, self.pool_cfg)
                connected = True
            else:
                print("AGENT CREATE POOL LEDGER ERROR: {}".format(e))
                connected = False
        print("AGENT: OPEN LEDGER AND GET HANDLE")
        self.pool_handle = await pool.open_pool_ledger(config_name=self.pool_name, config=None)
        print("AGENT FINISH CONNECT TO POOL")
        return connected

    async def verify_cred_offer(self,
                                their_did: str,
                                schema_id: str):
        # get_schema_request: str = await ledger.build_get_schema_request(
        #     their_did,
        #     schema_id)
        # get_schema_response: str = await ledger.submit_request(
        #     self.pool_handle,
        #     get_schema_request)
        # cred_def_schema = await ledger.parse_get_schema_response(get_schema_response)
        print("AGENT: This is the credential offer that we received!!!")
        # print(json.dumps(cred_def_schema['data']))

    async def prepare_credential_request(self,
                                         cred_def: str,
                                         cred_offer: str,
                                         my_did: str,
                                         their_did: str) -> (str, str):
        master_secret: str = ""
        generated_cred_def_request: str = ""
        generated_cred_def_response: str = ""

        try:
            secret_name = 'secret'   # secret put in wallet, this is just the name
            self.master_secret = await anoncreds.prover_create_master_secret(self.wallet_handle, secret_name)
            print("Agent: Got master key in wallet. Preparing to bind it and send to Issuer.")
            # credential request is generated
            my_cred_request, cred_request_metadata = \
                await anoncreds.prover_create_credential_req(self.wallet_handle,
                                                             my_did,
                                                             cred_offer,
                                                             cred_def,
                                                             secret_name)

            print("Agent: my_cred_request: ", my_cred_request)
            print("Agent: my_cred_request_metadata: ", cred_request_metadata)

            return my_cred_request, cred_request_metadata
        except IndyError as e:
            print('Error occurred: %s' % e)


