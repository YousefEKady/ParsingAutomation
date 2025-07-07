from clickhouse_driver import Client
import os

CLICKHOUSE_HOST = os.getenv('CLICKHOUSE_HOST', 'scl9q69y9s.europe-west4.gcp.clickhouse.cloud')
CLICKHOUSE_PORT = int(os.getenv('CLICKHOUSE_PORT', 9440))
CLICKHOUSE_USER = os.getenv('CLICKHOUSE_USER', 'default')
CLICKHOUSE_PASSWORD = os.getenv('CLICKHOUSE_PASSWORD', 'KW8JCaEid~hj2')
CLICKHOUSE_DATABASE = os.getenv('CLICKHOUSE_DATABASE', 'default')


def get_clickhouse_client():
    return Client(
        host=CLICKHOUSE_HOST,
        port=CLICKHOUSE_PORT,
        user=CLICKHOUSE_USER,
        password=CLICKHOUSE_PASSWORD,
        database=CLICKHOUSE_DATABASE,
        secure=True
    ) 