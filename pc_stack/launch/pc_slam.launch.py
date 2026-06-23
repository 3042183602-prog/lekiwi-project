#!/usr/bin/env python3
"""
Launch PC-side sensor fusion: rf2o laser odometry + EKF.

Designed to run on the PC alongside the Pi's hardware stack.
Subscribes to Pi topics via DDS (ROS_DOMAIN_ID must match):
  - /scan                       (sensor_msgs/LaserScan)   from LiDAR (5Hz)
  - /base_controller/odom       (nav_msgs/Odometry)       from wheel odometry
  - /imu_sensor_broadcaster/imu (sensor_msgs/Imu)         from IMU (YB-IMU)

Pipeline:
  1) rf2o reads /scan and publishes /laser_odom (x/y pose from scan matching)
  2) EKF fuses wheel vx/vy + IMU orientation/angular rates + rf2o x/y
     → publishes /odometry/filtered + odom → base_footprint TF

Usage:
  ros2 launch lekiwi_navigation pc_slam.launch.py
"""

from launch import LaunchDescription
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    # Path to EKF config
    ekf_config = PathJoinSubstitution([
        FindPackageShare('lekiwi_navigation'),
        'config', 'robot_localization', 'ekf_rf2o.yaml',
    ])

    # ── rf2o: laser scan odometry ──────────────────────────────────
    # Outputs /laser_odom (x/y position) from scan matching.
    # publish_tf=false: EKF owns odom→base_footprint TF.
    rf2o = Node(
        package='rf2o_laser_odometry',
        executable='rf2o_laser_odometry_node',
        name='rf2o_laser_odometry',
        output='screen',
        parameters=[{
            'laser_scan_topic':  '/scan',
            'odom_topic':        '/laser_odom',
            'publish_tf':        False,
            'base_frame_id':     'base_link',
            'odom_frame_id':     'odom',
            'init_pose_from_topic': '',
            'freq':              5.0,    # match LiDAR rate (LD19 @ 5Hz)
        }],
    )

    # ── EKF: sensor fusion ─────────────────────────────────────────
    # Fuses: wheel vx/vy + IMU orientation/angular rates + rf2o x/y
    # Publishes: /odometry/filtered + odom→base_footprint TF
    ekf = Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_node',
        output='log',
        parameters=[ekf_config],
        arguments=['--ros-args', '--log-level', 'rclcpp:=ERROR'],
    )

    return LaunchDescription([rf2o, ekf])
