from setuptools import setup, find_packages

import os
from glob import glob
package_name = 'web_control'

setup(
    name=package_name,
    version='0.1.0',

    packages=find_packages(),

    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),

        ('share/' + package_name + '/templates', [
            'templates/index.html',
            'templates/run.html'
        ]),

        ('share/' + package_name + '/static', [
            'static/style.css'
        ]),

        ('share/' + package_name + '/static/js', [
            'static/js/status.js',
            'static/js/joystick.js',
            'static/js/app.js'
        ]),

        (os.path.join('share', 'web_control', 'ai_modes', 'resources', 'audio'),
        glob('web_control/ai_modes/resources/audio/*.wav')),
    ],

    install_requires=['setuptools'],
    zip_safe=True,

    maintainer='basel',
    maintainer_email='basel@example.com',

    description='TurboPi Web UI (Home + Run) with gaming style and status panel',
    license='MIT',

    entry_points={
        'console_scripts': [
            'web_control_node = web_control.web_control_node:main',
            'avoidance_node = web_control.autonomous.avoidance_node:main',
            'scan_and_find_node = web_control.autonomous.scan_and_find_node:main', 
            'joystick_node = web_control.joystick.joystick_node:main',
            'ai_assistant_node = web_control.ai_modes.nodes.ai_assistant_node:main',
        ],
    },
)
