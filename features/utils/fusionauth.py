import requests
from softozor_test_utils.timing import fail_after_timeout


def fusionauth_is_up(fusionauth_ip, fusionauth_port, timeout_in_sec=300, period_in_sec=15):
    def test_is_up():
        try:
            response = requests.get(
                f'http://{fusionauth_ip}:{fusionauth_port}/api/status')
            return response.status_code == 200
        except:
            return False

    return fail_after_timeout(lambda: test_is_up(), timeout_in_sec, period_in_sec)


def create_user(client, user):
    response = client.create_user({
        'sendSetPasswordEmail': False,
        'user': {
            'email': user['email'],
            'password': user['password']
        }
    }, user['id'])
    if response.was_successful() is False:
        user_id = user['id']
        print(f'cannot create user with id <{user_id}>')
        print('error: ', response.error_response)


def register_user(client, user, app_id, roles):
    response = client.register({
        'registration': {
            'applicationId': app_id,
            'roles': roles
        }
    }, user['id'])
    if response.was_successful() is False:
        user_id = user['id']
        print(
            f'cannot register user with id <{user_id}> on application <{app_id}>')
        print('error: ', response.error_response)


def delete_registration(client, user_id, app_id):
    response = client.delete_registration(user_id, app_id)
    if response.was_successful() is False:
        print(f'cannot unregister user id <{user_id}> from app id <{app_id}>')
        print('error: ', response.error_response)


def retrieve_user(client, user_id):
    response = client.retrieve_user(user_id)
    if response.was_successful() is False:
        print(f'cannot retrieve user with id <{user_id}>')
        print('error: ', response.error_response)
        return None
    return response.success_response['user']


def delete_user(client, user_id):
    response = client.delete_user(user_id)
    if response.was_successful() is False:
        print(f'cannot remove user with id <{user_id}>')
        print('error: ', response.error_response)
