#!/usr/bin/env python3
"""
One-click launch for LeKiwi base: motor control + YbImu IMU + LiDAR.

Equivalent to running:
    ros2 launch lekiwi_bringup lekiwi.launch.py config:=base use_ybimu:=true
    ros2 launch lekiwi_bringup laser.launch.py
in a single command.
"""

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.substitutions import FindPackageShare


def launch_setup(context, *args, **kwargs):
    pkg_bringup = FindPackageShare('lekiwi_bringup').perform(context)

    def include(pkg, path, args=None):
        return IncludeLaunchDescription(
            PythonLaunchDescriptionSource([f'{pkg}/{path}']),
            launch_arguments=(args or {}).items(),
        )

    # Base control stack + YbImu (use_ybimu=true)
    control = include(
        pkg_bringup,
        'launch/lekiwi.launch.py',
        {'config': 'base', 'use_ybimu': 'true'},
    )

    # LiDAR (YDLiDAR X3)
    laser = include(pkg_bringup, 'launch/laser.launch.py')

    return [control, laser]


def generate_launch_description():
    return LaunchDescription([OpaqueFunction(function=launch_setup)])
