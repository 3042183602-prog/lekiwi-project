#!/usr/bin/env python3
"""
PC 侧全栈启动：rf2o + EKF + SLAM Toolbox / Nav2

依赖：树莓派已启动硬件并发布 /scan, /base_controller/odom, /imu_sensor_broadcaster/imu
两台机器 ROS_DOMAIN_ID 必须一致（默认 7）。

两种模式：
  mode:=slam   — 建图模式：rf2o + EKF + slam_toolbox online_async + Rviz2
  mode:=nav    — 导航模式：rf2o + EKF + nav2 全套（slam_toolbox + 规划/控制/避障）+ Rviz2

启动示例：
  # 建图
  ros2 launch lekiwi_navigation pc_full.launch.py mode:=slam

  # 导航（跑之前确保已有一张地图）
  ros2 launch lekiwi_navigation pc_full.launch.py mode:=nav

  # 关闭 Rviz2
  ros2 launch lekiwi_navigation pc_full.launch.py mode:=slam use_rviz:=false
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def launch_setup(context, *args, **kwargs):
    mode = LaunchConfiguration('mode').perform(context)
    use_rviz = LaunchConfiguration('use_rviz').perform(context)
    use_sim_time = LaunchConfiguration('use_sim_time').perform(context)

    pkg_nav = FindPackageShare('lekiwi_navigation').perform(context)

    def ekf_config(name):
        return PathJoinSubstitution([
            FindPackageShare('lekiwi_navigation'),
            'config', 'robot_localization', name,
        ])

    # ── 1. rf2o: laser scan odometry ────────────────────────────
    rf2o = Node(
        package='rf2o_laser_odometry',
        executable='rf2o_laser_odometry_node',
        name='rf2o_laser_odometry',
        output='screen',
        parameters=[{
            'laser_scan_topic':    '/scan',
            'odom_topic':          '/laser_odom',
            'publish_tf':          False,
            'base_frame_id':       'base_link',
            'odom_frame_id':       'odom',
            'init_pose_from_topic': '',
            'freq':                5.0,
        }],
    )

    # ── 2. EKF: sensor fusion ───────────────────────────────────
    ekf = Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_node',
        output='log',
        parameters=[ekf_config('ekf_rf2o.yaml')],
        arguments=['--ros-args', '--log-level', 'rclcpp:=ERROR'],
    )

    actions = [rf2o, ekf]

    # ── 3. slam_toolbox (always — used for map in slam mode,     ──
    # ──    for localization + mapping in nav mode)               ──
    slam_config = PathJoinSubstitution([
        FindPackageShare('lekiwi_navigation'),
        'config', 'slam.yaml',
    ])
    slam_toolbox = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        parameters=[slam_config],
    )
    actions.append(slam_toolbox)

    # ── 4. Navigation stack (nav mode only) ─────────────────────
    if mode == 'nav':
        nav2_params = PathJoinSubstitution([
            FindPackageShare('lekiwi_navigation'),
            'config', 'nav2.yaml',
        ])
        nav2_dir = get_package_share_directory('nav2_bringup')

        # Nav2 navigation stack (controller, planner, BT, costmaps, etc.)
        # slam_toolbox already running → provides /map for global_costmap static_layer
        nav2_nav_launch = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(nav2_dir, 'launch', 'navigation_launch.py')
            ),
            launch_arguments={
                'use_sim_time': use_sim_time,
                'params_file': os.path.join(pkg_nav, 'config', 'nav2.yaml'),
                'autostart': 'true',
                'use_composition': 'False',
                'use_respawn': 'False',
                'namespace': '',
            }.items(),
        )
        actions.append(nav2_nav_launch)

    # ── 5. Rviz2 (optional) ─────────────────────────────────────
    if use_rviz.lower() == 'true':
        nav2_bringup_dir = get_package_share_directory('nav2_bringup')
        rviz_config = os.path.join(nav2_bringup_dir, 'rviz', 'nav2_default_view.rviz')
        rviz = Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='log',
            arguments=['-d', rviz_config],
        )
        actions.append(rviz)

    return actions


def generate_launch_description():
    declared_arguments = [
        DeclareLaunchArgument(
            'mode',
            default_value='slam',
            description='Operation mode: "slam" (建图) or "nav" (导航)',
        ),
        DeclareLaunchArgument(
            'use_rviz',
            default_value='true',
            description='Launch Rviz2 for visualization',
        ),
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='false',
            description='Use simulation clock',
        ),
    ]

    return LaunchDescription(declared_arguments + [OpaqueFunction(function=launch_setup)])
