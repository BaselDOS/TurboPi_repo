from setuptools import setup

package_name = 'web_control'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
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
        ],
    },
)
