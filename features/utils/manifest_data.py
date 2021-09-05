def get_manifest_data(success_text):
    if not success_text:
        return {}

    manifest_data = {}
    for key_value in success_text.split('\n'):
        key, value = key_value.split(':')
        key = key.replace('<strong>', '')
        key = key.replace('</strong>', '')
        manifest_data[key] = value

    return manifest_data
