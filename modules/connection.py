from indy import crypto, did, pairwise, non_secrets, error
from message import Message
import serializer.json_serializer as Serializer
import base64
import datetime
import json
import indy_sdk_utils as utils
from indy_sdk_utils import create_and_store_my_did


class BadInviteException(Exception):
    def __init__(self, msg):
        super().__init__(msg)


class Connection:
    '''
    Connection class creates a connection between users by generating invitations, receiving the invitation, and
    having the invitation be accepted.
    '''
    def __init__(self, agent):
        self.agent = agent

    async def generate_invite(self):
        '''
        Creates an invitation code to be send to the other user to process.
        '''
        connection_key = await did.create_key(self.agent.wallet_handle, "{}")
        print("Connection Key: ", connection_key)

        # store key
        await non_secrets.add_wallet_record(self.agent.wallet_handle,
                                            'connection_key',
                                            connection_key,
                                            connection_key,
                                            '{}')
        invite_msg = Message({
            '@type': "GENERATE_INVITE",
            'label': self.agent.owner,
            'initialized': self.agent.initialized,
            'recipientKeys': [connection_key],
        })
        print("INVITE_MSG: ", invite_msg)

        invite_code = \
            base64.urlsafe_b64encode(
                bytes(Serializer.pack(invite_msg), 'utf-8')).decode('ascii')
        return str(invite_code)

    async def recieve_invite(self, msg):
        '''
        Recieve invitation from user to create a pending connection.
        :param msg: code generated from user
        '''
        invite_msg = Serializer.unpack(
            base64.urlsafe_b64decode(msg).decode('utf-8'))

        print("\nMESSAGE RECEIVED: ", invite_msg)

        pending_connection = Message({
            '@type': "INVITE_RECEIVED",
            'label': invite_msg['label'],
            'connection_key': invite_msg['recipientKeys'][0],
            'history': [{
                'date': str(datetime.datetime.now()),
                'msg': invite_msg.to_dict()
            }],
            'status': "Invite Received"
        })
        print("\nPENDING CONNECTION", pending_connection)
        # Store invitation in the wallet
        await non_secrets.add_wallet_record(
            self.agent.wallet_handle,
            'invitations',
            invite_msg['recipientKeys'][0],
            Serializer.pack(pending_connection),
            '{}'
        )
        return True

    async def send_request(self, invitation):
        '''
        When button pressed, connection request is send to the other user.
        :param invitation: invitation from wallet record
        '''
        pending_connection = Serializer.unpack(     # recover invitation from wallet record
            json.loads(
                await non_secrets.get_wallet_record(
                    self.agent.wallet_handle,
                    'invitations',
                    invitation.get('connection_key'),
                    '{}'
                )
            )['value']
        )
        print("PENDING CONNECTION", pending_connection)

        my_label = self.agent.owner     # agent name
        label = pending_connection['label']     # name of other agent
        their_connection_key = pending_connection['connection_key']

        # create info for connection
        (my_did, my_vk) = await create_and_store_my_did(self.agent.wallet_handle)
        await did.set_did_metadata(
            self.agent.wallet_handle,
            my_did,
            json.dumps({
                'label': label
            })
        )

        # Send Connection Request to inviter
        request = Message({
            '@type': "SEND_REQUEST",
            '@sendTo': label,
            'label': my_label,
            'connection': {
                'DID': my_did,
                'DIDDoc': {
                    "@context": "https://w3id.org/did/v1",
                    "id": my_did,
                    "publicKey": [{
                        "id": my_did + "#keys-1",
                        "type": "Ed25519VerificationKey2018",
                        "controller": my_did,
                        "publicKeyBase58": my_vk
                    }],
                    "service": [{
                        "id": my_did + ";indy",
                        "type": "IndyAgent",
                        "recipientKeys": [my_vk],
                    }],
                }
            }
        })
        print("REQUEST", request)

        print("SEND MESSAGE TO END AND KEY")
        await self.agent.send_message_to_endpoint_and_key(      # Send request to other user
            my_vk,
            their_connection_key,
            request
        )

        # update pending request record
        pending_connection['@type'] = "REQUEST_SENT"
        pending_connection['status'] = "Request Sent"
        pending_connection['history'].append({
            'date': str(datetime.datetime.now()),
            'msg': Message(invitation).to_dict()})
        await non_secrets.update_wallet_record_value(self.agent.wallet_handle,
                                                     'invitations',
                                                     pending_connection['connection_key'],
                                                     Serializer.pack(pending_connection))

    async def send_response(self, msg):
        '''
        When clicking on send response button, response message is send to other user to create pairwise connection
        '''
        print("\nSEND RESPONSE")
        their_did = msg['did']
        # pairwise connection info
        pairwise_info = json.loads(await pairwise.get_pairwise(self.agent.wallet_handle, their_did))
        pairwise_meta = json.loads(pairwise_info['metadata'])
        my_did = pairwise_info['my_did']
        label = pairwise_meta['label']
        my_vk = await did.key_for_local_did(self.agent.wallet_handle, my_did)

        # response message generated
        response_msg = Message({
            '@type': "SEND_RESPONSE",
            '@sendTo': label,
            '~thread': {'thid': pairwise_meta['req_id']},
            'connection': {
                'DID': my_did,
                'DIDDoc': {
                    "@context": "https://w3id.org/did/v1",
                    "id": my_did,
                    "publicKey": [{
                        "id": my_did + "#keys-1",
                        "type": "Ed25519VerificationKey2018",
                        "controller": my_did,
                        "publicKeyBase58": my_vk
                    }],
                    "service": [{
                        "id": my_did + ";indy",
                        "type": "IndyAgent",
                        "recipientKeys": [my_vk],
                    }],
                }
            }
        })
        print("SEND RESPONSE: ", response_msg)

        # apply signature to connection field, sign with key used in invitation and request
        response_msg['connection~sig'] = await self.agent.sign_agent_message_field(response_msg['connection'], pairwise_meta['connection_key'])
        del response_msg['connection']

        pending_connection = Serializer.unpack(json.loads(
            await non_secrets.get_wallet_record(self.agent.wallet_handle, 'invitations',
                                                pairwise_meta['connection_key'], '{}'))['value']
                                               )
        pending_connection['status'] = "Response Sent"
        pending_connection['@type'] = "RESPONSE SENT"
        pending_connection['history'].append({
            'date': str(datetime.datetime.now()),
            'msg': Message(msg).to_dict()})

        # send message to agent
        await self.agent.send_message_to_agent(their_did, response_msg)
        # delete invitation from records
        await non_secrets.delete_wallet_record(self.agent.wallet_handle, 'invitations', pairwise_meta['connection_key'])

    async def request_recieved(self, msg):
        '''
        Request received from user to create pending connection.
        '''
        print("request received")
        connection_key = msg.context['to_key']
        label = msg['label']
        their_did = msg['connection']['DID']
        their_vk = msg['connection']['DIDDoc']['publicKey'][0]['publicKeyBase58']

        # store info from request
        await utils.store_their_did(self.agent.wallet_handle, their_did, their_vk)

        await did.set_did_metadata(
            self.agent.wallet_handle,
            their_did,
            json.dumps({
                'label': label,
            })
        )
        # Create my information for connection
        (my_did, my_vk) = await utils.create_and_store_my_did(self.agent.wallet_handle)

        # Create pairwise relationship between my did and their did
        await pairwise.create_pairwise(
            self.agent.wallet_handle,
            their_did,
            my_did,
            json.dumps({
                'label': label,
                'req_id': msg['@id'],
                'their_vk': their_vk,
                'my_vk': my_vk,
                'connection_key': connection_key  # used to sign the response
            })
        )
        # pending connection message
        pending_connection = Message({
            '@type': "REQUEST_RECIEVED",
            'label': label,
            'did': their_did,
            'connection_key': connection_key,
            'history': [{
                'date': str(datetime.datetime.now()),
                'msg': msg.to_dict()}],
            'status': "Request Received"
        })
        print("CONNECTION REQUEST_RECEIVED: PENDING CONN: ", pending_connection)
        # Create pending connection between users
        try:
            await non_secrets.add_wallet_record(
                self.agent.wallet_handle,
                'invitations',
                connection_key,
                Serializer.pack(pending_connection),
                '{}'
            )
        except error.IndyError as indy_error:
            if indy_error.error_code == error.ErrorCode.WalletItemAlreadyExists:
                pass
            raise indy_error

    async def response_recieved(self, msg: Message)->Message:
        '''
        Response is received from user and connection is set into place.
        '''
        print("\nresponse received")
        my_did = msg.context['to_did']
        my_vk = await did.key_for_local_did(self.agent.wallet_handle, my_did)

        # process signed field
        msg['connection'], sig_verified = await self.agent.unpack_and_verify_signed_agent_message_field(
            msg['connection~sig'])
        # connection~sig remains for metadata
        their_did = msg['connection']['DID']
        their_vk = msg['connection']['DIDDoc']['publicKey'][0]['publicKeyBase58']

        msg_vk = msg.context['from_key']

        # Retrieve connection information from DID metadata
        my_did_meta = json.loads(await did.get_did_metadata(self.agent.wallet_handle, my_did))
        label = my_did_meta['label']

        # Clear DID metadata. This info will be stored in pairwise meta.
        await did.set_did_metadata(self.agent.wallet_handle, my_did, '')

        # In the final implementation, a signature will be provided to verify changes to
        # the keys and DIDs to be used long term in the relationship.
        # Both the signature and signature check are omitted for now until specifics of the
        # signature are decided.

        # Store their information from response
        await utils.store_their_did(self.agent.wallet_handle, their_did, their_vk)

        await did.set_did_metadata(
            self.agent.wallet_handle,
            their_did,
            json.dumps({
                'label': label
            })
        )

        # Create pairwise relationship between my did and their did
        await pairwise.create_pairwise(
            self.agent.wallet_handle,
            their_did,
            my_did,
            json.dumps({
                'label': label,
                'their_vk': their_vk,
                'my_vk': my_vk,
                'connection_key': msg.data['connection~sig']['signer']
            })
        )
        # Retrieve pending connection from records
        pending_connection = Serializer.unpack(
            json.loads(
                await non_secrets.get_wallet_record(self.agent.wallet_handle,
                                                    'invitations',
                                                    msg.data['connection~sig']['signer'],
                                                    '{}'))['value'])
        pending_connection['status'] = "Response Received"
        pending_connection['@type'] = "RESPONSE_RECIEVED"
        pending_connection['history'].append({
            'date': str(datetime.datetime.now()),
            'msg': msg.to_dict()})
        print("CONNECTION RESPONSE_RECEIVED: PENDING CONN: ", pending_connection)

        # Pairwise connection between agents is established at this point
        # Delete invitation
        await non_secrets.delete_wallet_record(self.agent.wallet_handle,
                                               'invitations',
                                               msg.data['connection~sig']['signer'])