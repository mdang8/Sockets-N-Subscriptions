# Sockets-N-Subscriptions

Subscribe to an [AWS SNS](https://aws.amazon.com/sns/) topic using network sockets!

## Requirements

Only what's provided in the Python 3 standard library.

## Setup

Create an `env.ini` file in the project root directory with the following structure:

  ```ini
  [DEFAULT]
  LOG_LEVEL=
  LISTEN_PORT=
  SNS_HOST=
  SNS_REGION=
  SNS_TOPIC_ARN=
  AWS_ACCESS_KEY_ID=
  AWS_SECRET_KEY=
  ```

- `LOG_LEVEL` is the level of logging you want to be printed to the console. Use **INFO** for standard logging or **DEBUG** if you want a higher level of logs. Higher levels means more log statements will be printed and are not necessarily needed for normal usage.
- `LISTEN_PORT` is the port that the socket will bind to for listening. Try to choose one greater than 1023. In addition, the host the socket will be bound to is **127.0.0.1** by default.
- `SNS_HOST` is the hostname of the SNS topic you are subscribing to and is determined by the region it is located in. https://docs.aws.amazon.com/general/latest/gr/rande.html
- `SNS_REGION` is the AWS region the SNS topic is located in. https://docs.aws.amazon.com/sns/latest/dg/sns-supported-regions-countries.html
- `SNS_TOPIC_ARN` is the unique identifier for the SNS topic. https://docs.aws.amazon.com/general/latest/gr/aws-arns-and-namespaces.html
- `AWS_ACCESS_KEY` is your AWS access key id tied to your account.
- `AWS_SECRET_KEY` is your AWS secret key tied to your account.

## Usage

### List all the available topics you can subscribe to with your current configs:
```bash
python sockets_n_subscriptions.py --list-topics
```

### Create a new subscription and listen for messages:
```bash
python sockets_n_subscriptions.py --subscribe <SUBSCRIPTION_ENDPOINT>
```
- `SUBSCRIPTION_ENDPOINT` is the endpoint you are subscribing to the SNS topic. This will be where notifications are "sent" to and it will need to be a publicly exposed endpoint. For local use, [ngrok](https://ngrok.com/) or something similar will work.

### Only listen for messages:
_* requires a subscription to have already been created_
```bash
python sockets_n_subscriptions.py --listen
```
- Currently set to listen on localhost port `9081`
