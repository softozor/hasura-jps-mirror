import os

import psycopg2
from behave import *
from softozor_graphql_client import GraphQLClient
from softozor_test_utils.sockets import host_has_port_open
from test_utils.manifest_data import get_manifest_data

from features.utils.faas import deploy, is_function_ready, faas_is_up
from features.utils.fusionauth import fusionauth_is_up
from features.utils.hasura import hasura_is_up


@given(u'the user has installed the main manifest')
def step_impl(context):
    success_text = context.jps_client.install_from_file(
        context.main_manifest, context.current_env_name, settings={
            'hasuraVersion': context.hasura_version,
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
    database_node_ip = context.current_env_info.get_node_ip_from_name(
        'Primary')
    assert database_node_ip is not None
    admin_user = context.manifest_data['Database Admin User']
    admin_password = context.manifest_data['Database Admin Password']
    context.connections = {
        'hasura': psycopg2.connect(
            host=database_node_ip,
            user=admin_user,
            password=admin_password,
            database=context.hasura_database_name),
        'auth': psycopg2.connect(
            host=database_node_ip,
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


@given(u'its database metadata')
def step_impl(context):
    success = context.hasura_client.apply_metadata(
        context.path_to_hasura_project)
    assert success is True


@given(u'she has added a todo through the following graphql mutation')
def step_impl(context):
    mutation = context.text
    response, _ = context.graphql_client.execute(
        query=mutation, run_as_admin=False)
    context.current_todo_id = response['data']['insert_todos_one']['id']


@given(u'the user has applied the database migrations of the \'{project_name}\'')
def step_impl(context, project_name):
    context.path_to_hasura_project = os.path.join(
        context.hasura_projects_folder, project_name
    )
    success = context.hasura_client.apply_migrations(
        context.path_to_hasura_project)
    assert success is True


@given(u'the user has started the todo with the hasura action')
def step_impl(context):
    mutation = context.text
    variables = {
        'id': context.current_todo_id
    }
    response, _ = context.graphql_client.execute(
        query=mutation, variables=variables, run_as_admin=False)
    print('response = ', response)
    assert 'errors' not in response


@given(u'the \'hasura-action\' function has been deployed on the faas engine')
def step_impl(context):
    function_name = 'hasura-action'
    context.faas_client.login()
    context.current_faas_function = function_name
    deployment_success = deploy(
        context.faas_client,
        context.path_to_serverless_configuration,
        function_name,
        env={
            'GRAPHQL_ENDPOINT': context.internal_graphql_endpoint
        })
    assert deployment_success is True


@when(u'the user applies the database migrations of the \'{project_name}\'')
def step_impl(context, project_name):
    context.path_to_hasura_project = os.path.join(
        context.hasura_projects_folder, project_name
    )
    context.success = context.hasura_client.apply_migrations(
        context.path_to_hasura_project)


@when(u'she retrieves the new todo with the following query')
def step_impl(context):
    query = context.text
    variables = {
        'id': context.current_todo_id
    }
    response, _ = context.graphql_client.execute(
        query=query, variables=variables, run_as_admin=False)
    print('response = ', response)
    context.actual_todo = response['data']['todos_by_pk']


@then("fusionauth is available")
def step_impl(context):
    assert fusionauth_is_up(
        context.current_fusionauth_ip, context.fusionauth_port) is True


@then("the faas engine is available")
def step_impl(context):
    assert faas_is_up(context.faas_client) is True


@then("hasura is available")
def step_impl(context):
    assert hasura_is_up(
        context.hasura_node_ip, context.hasura_internal_port) is True


@then("the {function_name} function is ready")
def step_impl(context, function_name):
    assert is_function_ready(context.faas_client, function_name) is True


@then('the following extensions are installed on the {database_name} database')
def step_impl(context, database_name):
    expected_extensions = set(row['extension'] for row in context.table)
    cursor = context.connections[database_name].cursor()
    cursor.execute(
        """
        SELECT extname FROM pg_extension;
        """
    )
    fetched_rows = cursor.fetchall()
    actual_extensions = set(extension[0] for extension in fetched_rows)
    assert expected_extensions.intersection(
        actual_extensions) == expected_extensions


@then('the following schemas exist on the {database_name} database')
def step_impl(context, database_name):
    expected_schemas = set(row['schema'] for row in context.table)
    cursor = context.connections[database_name].cursor()
    cursor.execute(
        """
        SELECT schema_name FROM information_schema.schemata;
        """
    )
    fetched_rows = cursor.fetchall()
    actual_schemas = set(schema[0] for schema in fetched_rows)
    assert expected_schemas.intersection(actual_schemas) == expected_schemas


@then(u'there is {nb_nodes:d} {node_type} node in the {node_group} node group')
@then(u'there are {nb_nodes:d} {node_type} nodes in the {node_group} node group')
def step_impl(context, nb_nodes, node_type, node_group):
    node_ips = context.current_env_info.get_node_ips(
        node_group=node_group, node_type=node_type)
    assert len(node_ips) == nb_nodes


@then(u'she gets success')
def step_impl(context):
    assert context.success is True


@then(u'she gets the description')
def step_impl(context):
    expected_description = context.text
    actual_description = context.actual_todo['description']
    assert expected_description == actual_description


@then(u'she gets state \'{expected_state}\'')
@then(u'state \'{expected_state}\'')
def step_impl(context, expected_state):
    actual_state = context.actual_todo['state']
    assert expected_state == actual_state
