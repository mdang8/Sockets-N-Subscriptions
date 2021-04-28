import logging, socket, sys
from urllib.parse import urlencode
from json import decoder, loads

BUFFER_SIZE = 4096

class TopicListener:
    def __init__(self, logging_level, listen_host, listen_port, sns_host, signer):
        logging.basicConfig(
            format='%(asctime)s %(levelname)-8s %(message)s',
            level=logging_level,
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.sns_host = sns_host
        self.signer = signer
        self.listener_socket = None

    @staticmethod
    def format_header_str(headers: dict):
        """
        Takes a dict of HTTP headers and formats it into a string with the header pairs separated by newline.
        """
        return '\r\n'.join([f'{k}: {headers[k]}' for k in headers.keys()])

    @staticmethod
    def receive_msg(conn):
        """
        Receives the incoming data from the given socket in chunks of size BUFFER_SIZE.
        """
        msg_chunks = []
        while True:
            try:
                msg = conn.recv(BUFFER_SIZE)
            except socket.error as e:
                logging.debug(e)
                break
            if not msg or len(msg) <= 0:
                break
            msg_chunks.append(msg.decode('utf-8'))
        return ''.join(msg_chunks)

    @staticmethod
    def parse_resp_msg(msg):
        """
        Parses a response message to a tuple containing the request line, headers, and body.
        """
        request_line, headers_body = msg.split('\r\n', 1)
        headers, body = headers_body.split('\r\n\r\n', 1)
        return (request_line, headers, body)

    @staticmethod
    def parse_http_headers(headers_str):
        """
        Parses a headers string separated by newline into a dict.
        """
        headers = headers_str.split('\r\n')
        mapped_headers = {}
        for h in headers:
            split_h = h.split(': ', 1)
            # normalize header keys by converting to lower case
            mapped_headers[split_h[0].lower()] = split_h[1]
        return mapped_headers

    @staticmethod
    def parse_resp_body(body):
        """
        Parses a response body in JSON string format to a Python object (most likely a dict).
        """
        try:
            body = body.replace('\n', '')
            parsed_body = loads(body, strict=False)
        except decoder.JSONDecodeError:
            logging.error('Failed to parse incoming message.')
            return
        return parsed_body

    def handle_notification(self, body):
        """
        Gets the message value from a response body and prints it to the logger.
        """
        parsed_body = self.parse_resp_body(body)
        try:
            message = parsed_body['Message']
            logging.info(f'Message: {message}')
        except:
            logging.error('Failed to get message from parsed response.')
            return

    def handle_incoming_response(self, msg):
        """
        Parses a response and determines where to route the body to.
        """
        (resp_req_line, resp_headers, resp_body) = self.parse_resp_msg(msg)
        mapped_headers = self.parse_http_headers(resp_headers)

        if 'x-amz-sns-message-type' in mapped_headers:
            type = mapped_headers['x-amz-sns-message-type']
            if type == 'SubscriptionConfirmation':
                logging.debug('Received ConfirmSubscription message')
                self.confirm_subscription(resp_body)
            elif type == 'Notification':
                logging.debug('Received Notification message')
                self.handle_notification(resp_body)
            else:
                logging.debug('Received some other type of message!!!')
        else:
            logging.debug('Received an invalid message format.')

    def send_msg(self, method, host, headers, query_params=''):
        """
        Opens a new socket and sends an HTTP request based on the given arguments.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            try:
                ip = socket.gethostbyname(host)
            except socket.gaierror:
                logging.error('Error resolving the hostname')
                sys.exit(1)
            except Exception as e:
                logging.error(f'host: {host}')
                logging.error(e)
                sys.exit(1)
            s.connect((ip, 80))

            msg = f'{method} /?{query_params} HTTP/1.1\r\n{headers}\r\n\r\n'
            s.sendall(msg.encode())
            resp_msg = self.receive_msg(s)
            (resp_req_line, resp_headers, resp_body) = self.parse_resp_msg(resp_msg)
        return resp_body

    def close(self):
        """
        Closes the listening socket.
        """
        if self.listener_socket is not None:
            logging.debug('Closing listening socket.')
            self.listener_socket.close()

    def listen(self):
        """
        Opens a new socket for listening on the host/port. Receives/handles incoming messages from the SNS topic, and
        responds with a '200 OK' message.
        """
        self.listener_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listener_socket.bind((self.listen_host, self.listen_port))
        self.listener_socket.listen(1)

        logging.info(f'Listening on port {self.listen_port}...')
        while True:
            client_conn, client_addr = self.listener_socket.accept()
            client_conn.settimeout(1)
            logging.debug(f'Connection established with {client_addr}\n')
            msg = self.receive_msg(client_conn)
            client_conn.sendall(f'HTTP/1.1 200 OK\r\nHost: {self.sns_host}\r\n\r\n'.encode())
            self.handle_incoming_response(msg)
            client_conn.close()

    def list_available_topics(self, region):
        """
        Sends an HTTP request to AWS to retrieve the list of available SNS topics to subscribe to.
        """
        http_method = 'GET'
        query_str = 'Action=ListTopics'
        (auth_header, x_amz_date) = self.signer.generate_signed_req_headers(http_method, self.sns_host, region, 'sns', query_str)
        headers = {
            'Host': self.sns_host,
            'Connection': 'close',
            'x-amz-date': x_amz_date,
            'Authorization': auth_header
        }
        resp_body = self.send_msg(http_method, self.sns_host, self.format_header_str(headers), query_str)
        logging.info(resp_body)

    def subscribe_endpoint_to_topic(self, region, topic_arn, endpoint):
        """
        Sends an HTTP request to create a new subscription to the SNS topic.
        """
        http_method = 'GET'
        query_params = {
            'Action': 'Subscribe',
            'Endpoint': endpoint,
            'Protocol': 'http',
            'TopicArn': topic_arn
        }
        query_str = urlencode(query_params)
        (auth_header, x_amz_date) = self.signer.generate_signed_req_headers(http_method, self.sns_host, region, 'sns', query_str)
        headers = {
            'Host': self.sns_host,
            'x-amz-date': x_amz_date,
            'Authorization': auth_header
        }
        resp_body = self.send_msg(http_method, self.sns_host, self.format_header_str(headers), query_str)

    def confirm_subscription(self, body):
        """
        Sends an HTTP request to confirm a created subscription.
        """
        parsed_body = self.parse_resp_body(body)
        try:
            subscription_url = parsed_body['SubscribeURL']
        except:
            logging.error('Failed to get SubscriptionURL from parsed response.')
            return
        
        http_method = 'GET'
        [addr, query_str] = subscription_url.split('/?', 1)
        host = addr.split('https://', 1)[1]
        headers = {
            'Host': host
        }
        resp_body = self.send_msg(http_method, host, self.format_header_str(headers), query_str)
        logging.debug('Confirmed subscription to topic')
