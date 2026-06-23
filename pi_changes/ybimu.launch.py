#!/usr/bin/env python3
"""
Launch YbImu serial IMU node.

Reads data from a YbImu IMU over UART (pyserial) and publishes
sensor_msgs/Imu to /imu (and optionally /imu/mag).

Usage:
    ros2 launch lekiwi_bringup ybimu.launch.py port:=/dev/ttyUSB0
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    port_arg = DeclareLaunchArgument(
        'port',
        default_value='/dev/ttyUSB1',
        description='Serial port for YbImu IMU (e.g. /dev/ttyUSB0, /dev/ttyAMA0)',
    )

    config_file = PathJoinSubstitution([
        FindPackageShare('lekiwi_bringup'),
        'config',
        'ybimu.yaml',
    ])

    ybimu_node = Node(
        package='lekiwi_bringup',
        executable='ybimu_node',
        name='ybimu_node',
        output='screen',
        parameters=[config_file, {
            'port': LaunchConfiguration('port'),
        }],
        # Publish on the same topic as the BNO055 imu_sensor_broadcaster
        # so the existing EKF config works unchanged.
        remappings=[('imu', '/imu_sensor_broadcaster/imu')],
    )

    return LaunchDescription([
        port_arg,
        ybimu_node,
    ])
