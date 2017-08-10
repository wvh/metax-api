#!/usr/bin/env python
import pika

"""
for testing:

script to listen for messages sent when someone accesses /rest/datasets/pid/rabbitmq
"""

credentials = pika.PlainCredentials('testaaja', 'testaaja')
connection = pika.BlockingConnection(
    pika.ConnectionParameters(
        'localhost',
        5672,
        'metax',
        credentials))

channel = connection.channel()

exchange = 'datasets'
queue_1 = 'testaaja-create'
queue_2 = 'testaaja-update'

# note: requires write permission to exchanges
# channel.exchange_declare(exchange=exchange, type='fanout')

channel.queue_declare(queue_1, durable=True)
channel.queue_declare(queue_2, durable=True)

channel.queue_bind(exchange=exchange, queue=queue_1, routing_key='create')
channel.queue_bind(exchange=exchange, queue=queue_2, routing_key='update')

def callback_1(ch, method, properties, body):
    print(" [ create ] %r" % body)

def callback_2(ch, method, properties, body):
    print(" [ update ] %r" % body)

channel.basic_consume(callback_1, queue=queue_1, no_ack=True)
channel.basic_consume(callback_2, queue=queue_2, no_ack=True)

print('[*] Waiting for logs. To exit press CTRL+C')
channel.start_consuming()
