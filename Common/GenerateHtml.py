# -*- coding: utf-8 -*-
"""
@Time ： 2024-06-13 18:35
@Auth ： No2Cat
@File ：GenerateHtml.py
@IDE ：PyCharm
@DESC：
"""
def generate_basic_info_html(system_info):
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>基础信息</title>
    </head>
    <body>
        <h1>基础信息</h1>
        <h2>操作系统</h2>
        <p><strong>OS:</strong> {os}</p>
        <p><strong>Version:</strong> {os_version}</p>
        <p><strong>OS-INFO:</strong> {os_info}</p>
        <p><strong>HostName:</strong> {hostname}</p>
    """.format(os=system_info['os'], os_version=system_info['os_version'], os_info=system_info['os_info'], hostname=system_info['hostname'])

    html += """
        <h2>当前用户</h2>
        <p><strong>用户名:</strong> {user}</p>
        <p><strong>用户组:</strong> {group}</p>
        <p><strong>用户权限:</strong> {permissions}</p>
    """.format(user=system_info['current_user']['user'], group=system_info['current_user']['group'], permissions=system_info['current_user']['permissions'])

    if 'disk_info' in system_info and system_info['os'].lower() == 'windows':
        html += "<h2>磁盘信息</h2><ul>"
        for disk in system_info['disk_info']:
            html += """
            <li>
                <strong>磁盘:</strong> {device}<br>
                <strong>总量:</strong> {total} bytes<br>
                <strong>已使用:</strong> {used} bytes<br>
                <strong>未使用:</strong> {free} bytes<br>
                <strong>使用百分比:</strong> {percent:.2f}%
            </li>
            """.format(device=disk['device'], total=disk['total'], used=disk['used'], free=disk['free'], percent=disk['percent'])
        html += "</ul>"

    html += """
        <h2>当前路径</h2>
        <p>{current_path}</p>
    """.format(current_path=system_info['current_path'])

    html += "<h2>网卡信息</h2><ul>"
    for net in system_info['net_info']:
        html += """
        <li>
            <strong>Interface:</strong> {interface}  ---  <strong>IP Address:</strong> {ip_address}
        </li>
        """.format(interface=net['interface'], ip_address=net['ip_address'])
    html += "</ul>"

    html += "<h2>环境变量</h2><ul>"
    for key, value in system_info['env_vars'].items():
        html += """
        <li>
            <strong>{key}:</strong> {value}
        </li>
        """.format(key=key, value=value)
    html += "</ul>"

    html += """
    </body>
    </html>
    """
    return html