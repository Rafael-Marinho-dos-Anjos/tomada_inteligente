def generate_card(device_description, session_token, device_token):
    if len(device_description) > 20:
        device_description = device_description[:20]

    html_code = '<div class="device-card">'
    html_code += '<div class="device-description">'
    html_code += '<p class="device-text">{}</p>'.format(device_description)
    html_code += '<p class="device-text">{}</p>'.format(device_token)
    html_code += '</div>'
    html_code += '<form action="/tomadas/{}/{}/">'.format(session_token, device_token)
    html_code += '<button type="submit">Expandir</button>'
    html_code += '</form>'
    html_code += '</div>'

    return html_code