import signal, sys
from configparser import ConfigParser
from aws_signer import AwsSigner
from topic_listener import TopicListener

def handle_sigint(sig, frame):
    """
    Closes the listener socket and exits the program.
    """
    listener.close()
    sys.exit(0)


if __name__ == '__main__':
    try:
        config = ConfigParser()
        config.read('env.ini')
        log_level = config['DEFAULT']['LOG_LEVEL']
        listen_port = int(config['DEFAULT']['LISTEN_PORT'])
        sns_host = config['DEFAULT']['SNS_HOST']
        sns_region = config['DEFAULT']['SNS_REGION']
        sns_topic_arn = config['DEFAULT']['SNS_TOPIC_ARN']
        aws_access_key = config['DEFAULT']['AWS_ACCESS_KEY_ID']
        aws_secret_key = config['DEFAULT']['AWS_SECRET_KEY']
    except:
        print('There was an issue reading your config INI. Check the README for the correct format.')
        sys.exit(1)

    try:
        args = sys.argv[1:]
    except:
        print('There was an issue reading your CLI arguments. Check the README for the correct format.')
        sys.exit(1)

    # exit on SIGINT (e.g. when Ctrl-C is clicked)
    signal.signal(signal.SIGINT, handle_sigint)
    signer = AwsSigner(aws_access_key, aws_secret_key)
    listener = TopicListener(log_level, '127.0.0.1', listen_port, sns_host, signer)

    if args[0] == '--list-topics':
        listener.list_available_topics(sns_region)
    elif args[0] == '--listen':
        listener.listen()
    elif args[0] == '--subscribe' and args[1]:
        listener.subscribe_endpoint_to_topic(sns_region, sns_topic_arn, args[1])
        listener.listen()
    else:
        print('Invalid CLI argument.')
        sys.exit(1)
