import os
import random

import psycopg2
from behave import fixture
from faas_client import FaasClientFactory
from fusionauth.fusionauth_client import FusionAuthClient
from hasura_client import HasuraClientFactory
from jelastic_client import JelasticClientFactory
from softozor_graphql_client import GraphQLClient
from softozor_test_utils import host_has_port_open
from test_utils import get_new_random_env_name
from test_utils.manifest_data import get_manifest_data

from features.utils.fusionauth import create_user, register_user, delete_registration, delete_user


@fixture
def random_seed(context):
    random.seed('hasura-jps-tests')


@fixture
def worker_id(context):
    context.worker_id = 'master'
    return context.worker_id


@fixture
def base_url(context):
    userdata = context.config.userdata
    context.base_url = userdata['base-url']
    return context.base_url


@fixture
def commit_sha(context):
    userdata = context.config.userdata
    context.commit_sha = userdata['commit-sha']
    return context.commit_sha


@fixture
def project_root_folder(context):
    userdata = context.config.userdata
    context.project_root_folder = userdata['project-root-folder'] if 'project-root-folder' in userdata else '.'
    return context.project_root_folder


@fixture
def api_clients(context):
    userdata = context.config.userdata
    api_url = userdata['api-url']
    api_token = userdata['api-token']
    api_client_factory = JelasticClientFactory(api_url, api_token)
    context.jps_client = api_client_factory.create_jps_client()
    context.control_client = api_client_factory.create_control_client()
    context.file_client = api_client_factory.create_file_client()


@fixture
def faas_port(context):
    context.faas_port = 8080
    return faas_port


def path_to_serverless_test_configuration(context):
    context.path_to_serverless_test_configuration = os.path.join(
        context.project_root_folder, 'features', 'data', 'functions', 'faas.yml')
    return context.path_to_serverless_test_configuration


@fixture
def faas_client_factory(context):
    context.faas_client_factory = FaasClientFactory(
        context.faas_port)
    return context.faas_client_factory


@fixture
def fusionauth_version(context):
    userdata = context.config.userdata
    context.fusionauth_version = userdata['fusionauth-version']
    return context.fusionauth_version


@fixture
def fusionauth_port(context):
    context.fusionauth_port = 9011
    return fusionauth_port


@fixture
def fusionauth_admin_email(context):
    context.fusionauth_admin_email = 'admin@company.com'
    return context.fusionauth_admin_email


@fixture
def fusionauth_issuer(context):
    context.fusionauth_issuer = 'company.com'
    return context.fusionauth_issuer


@fixture
def main_manifest(context):
    context.main_manifest = os.path.join(
        context.project_root_folder, 'manifest.yml')
    return context.main_manifest


@fixture
def jelastic_environment(context):
    context.current_env_name = get_new_random_env_name(
        context.control_client, context.commit_sha, context.worker_id)

    success_text = context.jps_client.install_from_file(
        context.main_manifest, context.current_env_name, settings={
            'graphqlEngineTag': context.commit_sha,
            'fusionauthVersion': context.fusionauth_version,
            'authAdminEmail': context.fusionauth_admin_email,
            'authIssuer': context.fusionauth_issuer,
            'fncTag': context.commit_sha
        })
    context.current_env_info = context.control_client.get_env_info(
        context.current_env_name)
    assert context.current_env_info.is_running()
    context.hasura_node_ip = context.current_env_info.get_node_ips(node_group='cp')[
        0]
    external_api_endpoint = f'http://{context.current_env_info.domain()}/v1/graphql'
    internal_hasura_endpoint = f'http://{context.hasura_node_ip}:{context.hasura_internal_port}'
    context.internal_graphql_endpoint = f'{internal_hasura_endpoint}/v1/graphql'
    context.manifest_data = get_manifest_data(success_text)
    hasura_admin_secret = context.manifest_data['Hasura Admin Secret']
    assert host_has_port_open(context.hasura_node_ip,
                              context.hasura_internal_port)
    context.hasura_client = context.hasura_client_factory.create(
        internal_hasura_endpoint, hasura_admin_secret)
    context.graphql_client = GraphQLClient(
        external_api_endpoint, hasura_admin_secret)
    primary_node_ip = context.current_env_info.get_node_ip_from_name('Primary')
    assert primary_node_ip is not None
    secondary_node_ip = context.current_env_info.get_node_ip_from_name(
        'Secondary')
    assert secondary_node_ip is not None
    admin_user = context.manifest_data['Database Admin User']
    admin_password = context.manifest_data['Database Admin Password']
    context.connections = {
        'primary': psycopg2.connect(
            host=primary_node_ip,
            user=admin_user,
            password=admin_password,
            database=context.hasura_database_name),
        'secondary': psycopg2.connect(
            host=secondary_node_ip,
            user=admin_user,
            password=admin_password,
            database=context.hasura_database_name),
        'hasura': psycopg2.connect(
            host=primary_node_ip,
            user=admin_user,
            password=admin_password,
            database=context.hasura_database_name),
        'auth': psycopg2.connect(
            host=primary_node_ip,
            user=admin_user,
            password=admin_password,
            database=context.fusionauth_database_name)
    }
    faas_node_type = 'docker'
    faas_node_group = 'faas'
    faas_node_ip = context.current_env_info.get_node_ips(
        node_type=faas_node_type, node_group=faas_node_group)[0]
    assert host_has_port_open(faas_node_ip, context.faas_port)
    username = context.file_client.read(
        context.current_env_name,
        '/var/lib/faasd/secrets/basic-auth-user',
        node_type=faas_node_type,
        node_group=faas_node_group)
    password = context.file_client.read(
        context.current_env_name,
        '/var/lib/faasd/secrets/basic-auth-password',
        node_type=faas_node_type,
        node_group=faas_node_group)
    context.faas_client = context.faas_client_factory.create(
        faas_node_ip, username, password)
    context.current_fusionauth_ip = context.current_env_info.get_node_ips(
        node_group='auth', node_type='docker')[0]
    assert host_has_port_open(
        context.current_fusionauth_ip, context.fusionauth_port)
    api_key = context.manifest_data['Auth Almighty API Key']
    auth_url = f'http://{context.current_fusionauth_ip}:{context.fusionauth_port}'
    context.fusionauth_client = FusionAuthClient(api_key, auth_url)

    yield context.current_env_name

    # TODO: reactivate
    # env_info = context.control_client.get_env_info(
    #     context.current_env_name)
    # if env_info.exists():
    #     context.control_client.delete_env(context.current_env_name)


@fixture
def hasura_database_name(context):
    context.hasura_database_name = 'hasura'
    return context.hasura_database_name


@fixture
def fusionauth_database_name(context):
    context.fusionauth_database_name = 'fusionauth'
    return context.fusionauth_database_name


@fixture
def database_user(context):
    context.database_user = 'hasura_user'
    return context.database_user


@fixture
def database_password(context):
    context.database_password = 'admin_password'
    return context.database_password


@fixture
def close_database_connections(context):
    yield
    if hasattr(context, 'connections'):
        for database_connection in context.connections.values():
            database_connection.close()


@fixture
def hasura_client_factory(context):
    context.hasura_client_factory = HasuraClientFactory(
        'default')
    return context.hasura_client_factory


@fixture
def hasura_internal_port(context):
    context.hasura_internal_port = '8080'
    return context.hasura_internal_port


@fixture
def auth_test_application(context):
    # get lambda id
    response = context.fusionauth_client.retrieve_lambdas()
    assert response.was_successful() is True
    lambda_id = response['lambdas'][0]['id']

    # get access key id
    response = context.fusionauth_client.retrieve_keys()
    assert response.was_successful() is True
    key_id = response['keys'][0]['id']

    # create application
    response = context.fusionauth_client.create_application(request={
        "application": {
            "jwtConfiguration": {
                "accessTokenKeyId": key_id,
                "enabled": True,
                "refreshTokenTimeToLiveInMinutes": 1440,
                "timeToLiveInSeconds": 3600
            },
            "lambdaConfiguration": {
                "accessTokenPopulateId": lambda_id
            },
            "loginConfiguration": {
                "allowTokenRefresh": True,
                "generateRefreshTokens": True,
                "requireAuthentication": True
            },
            "name": "test-application",
            "roles": [
                {
                    "isDefault": True,
                    "isSuperRole": False,
                    "name": "user"
                }
            ]
        }
    })
    assert response.was_successful() is True
    context.auth_test_application = response['application']['id']

    yield context.auth_test_application

    # delete application
    response = context.fusionauth_client.delete_application(
        context.auth_test_application)
    assert response.was_successful() is True


@fixture
def registered_user_on_test_application(context):
    test_application_id = context.auth_test_application
    context.registered_user_on_test_application = {
        'username': 'user@company.com',
        'password': 'password'
    }
    user_id = create_user(context.fusionauth_client,
                          context.context.registered_user_on_test_application)
    register_user(context.fusionauth_client, user_id, test_application_id, [
        'user'
    ])
    yield context.registered_user_on_test_application
    # delete user + registration
    delete_registration(context.fusionauth_client,
                        user_id, test_application_id)
    delete_user(context.fusionauth_client, user_id)


fixtures_registry = {
    'jelastic-environment': jelastic_environment,
    'auth-test-application': auth_test_application,
    'registered-user-on-test-application': registered_user_on_test_application
}
