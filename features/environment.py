from fixtures import *

from behave import use_fixture
from behave.fixture import use_fixture_by_tag


def before_tag(context, tag):
    if tag.startswith('fixture.'):
        return use_fixture_by_tag(tag[8:], context, fixtures_registry)


def before_all(context):
    use_fixture(api_clients, context)
    use_fixture(random_seed, context)
    use_fixture(worker_id, context)
    use_fixture(commit_sha, context)
    use_fixture(project_root_folder, context)
    use_fixture(serverless_manifest, context)
    use_fixture(faas_port, context)


def before_scenario(context, scenario):
    use_fixture(new_environment, context)
    pass
