import socket
from threading import Thread

HEADER_LENGTH = 10
client_socket = None


def connect(ip, port, my_username, error_callback):
    '''
    Connect to the server
    '''

    global client_socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        # Connect to a given ip and port
        client_socket.connect((ip, port))
    except Exception as e:
        # Connection error
        error_callback('Connection error: {}'.format(str(e)))
        return False

    # encode username to bytes, then count number of bytes and prepare header of fixed size, that encode to bytes
    username = my_username.encode('utf-8')
    username_header = f"{len(username):<{HEADER_LENGTH}}".encode('utf-8')
    client_socket.send(username_header + username)
    return True


def send(message):
    '''
    Send a message to the server
    '''
    # Encode message to bytes, prepare header and convert to bytes, then send
    message_header = f"{len(message):<{HEADER_LENGTH}}".encode('utf-8')
    client_socket.send(message_header + message)


def start_listening(incoming_message_callback, error_callback):
    '''
    Start listening
    incoming_message_callback - callback to be called when new message arrives
    error_callback - callback to be called on error
    '''
    Thread(target=listen, args=(incoming_message_callback, error_callback), daemon=True).start()


def listen(incoming_message_callback, error_callback):
    '''
    Listen for incoming messages
    '''
    while True:

        try:
            while True:
                # Receive our "header" containing username length
                username_header = client_socket.recv(HEADER_LENGTH)

                # If no data received, server  closed a connection
                if not len(username_header):
                    error_callback('Connection closed by the server')

                # Convert header to int value
                username_length = int(username_header.decode('utf-8').strip())
                # Receive and decode username
                username = client_socket.recv(username_length).decode('utf-8')

                message_header = client_socket.recv(HEADER_LENGTH)
                message_length = int(message_header.decode('utf-8').strip())
                message = client_socket.recv(message_length).decode('utf-8')
                print("\n\nCLIENT MSG: ", message)

                # Print message
                incoming_message_callback(username, message)

        except Exception as e:
            # Any other exception - something happened, exit
            error_callback('Reading error: {}'.format(str(e)))