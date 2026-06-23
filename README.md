# LeKiwi Project

> 基于开源机器人平台 LeKiwi 的硬件适配与感知/导航系统集成。

本项目**不是从零开发**的机器人项目。LeKiwi 机器人底层基于 [adityakamath/lekiwi_ros2](https://github.com/adityakamath/lekiwi_ros2) 开源项目，我们在此基础上做了硬件替换、系统调优和上层感知导航栈的集成。

---

## 背景

### 原始状态

LeKiwi 底盘在原始状态下使用：
- **IMU：** BNO055（通过 bno055_hardware_interface 接入 ros2_control）
- **激光雷达：** LD19（10Hz，range_max=64m）
- **计算：** 全部运行在树莓派上（含 EKF、SLAM）

### 我们做的主要变更

#### 硬件替换

| 硬件 | 原来 | 现在 | 原因 |
|---|---|---|---|
| IMU | BNO055 | **YB-IMU** | 原传感器更换 |
| 激光雷达 | LD19 | **YDLiDAR X3**（5Hz, 8m） | 原传感器更换 |

#### 架构变更

将感知与导航的计算任务从树莓派迁移到 PC，形成分布式架构：

```
树莓派 (仅硬件驱动)              PC (感知 + 决策 + 导航)
                                  
  base_controller ──/odom──────┐
  ybimu_node ────/imu──────────┤── DDS ──→ EKF → /odometry/filtered + odom→base_footprint TF
  ldlidar_node ──/scan─────────┘          ↓
                                    rf2o → /laser_odom → x/y 位置修正
                                             ↓
                                       SLAM Toolbox → /map + map→odom TF
                                             ↓
                                       Nav2 → /cmd_vel ──DDS──→ 树莓派 base_controller 执行
```

这种架构的优点是：
- 树莓派只负责实时控制（确定性任务），减轻负载
- PC 处理计算密集型任务（SLAM、路径规划、模型推理）
- 通过 ROS 2 DDS 通信（ROS_DOMAIN_ID=7），对开发者透明

---

## 目录结构

```
lekiwi-project/
│
├── pi_changes/                 ← 树莓派侧：我们改过或新增的文件
│   ├── base_complete.launch.py    一键启动（base + YbIMU + 激光雷达）
│   ├── laser.yaml                 YDLiDAR X3 参数配置
│   └── ybimu.launch.py            YB-IMU 启动文件（含话题 remap）
│
├── pc_stack/                   ← PC 侧：我们新建的感知导航配置文件
│   ├── config/
│   │   ├── slam.yaml               SLAM Toolbox 参数
│   │   ├── nav2.yaml               Nav2 全栈参数
│   │   └── robot_localization/
│   │       └── ekf_rf2o.yaml       EKF 三源融合策略
│   └── launch/
│       ├── pc_slam.launch.py       轻量版：rf2o + EKF
│       └── pc_full.launch.py       全栈版：rf2o + EKF + SLAM + Nav2 + Rviz2
│
└── README.md
```

---

## 各文件详细说明

### Pi 侧（pi_changes/）

#### `base_complete.launch.py` — **新增** 一键启动文件

原来需要两个终端分别跑：
```bash
# 终端1
ros2 launch lekiwi_bringup lekiwi.launch.py config:=base use_ybimu:=true

# 终端2
ros2 launch lekiwi_bringup laser.launch.py
```

现在一个命令搞定：
```bash
ros2 launch lekiwi_bringup base_complete.launch.py
```

启动内容包括：base_controller（底盘控制）+ ybimu_node（IMU）+ ldlidar_node（激光雷达）。**注意：config:=base 模式下原本就不包含 EKF，所以这里也没有 EKF。**

#### `laser.yaml` — **修改** YDLiDAR X3 参数

原始配置面向 LD19（10Hz, range_max=64.0），替换为 YDLiDAR X3 后的参数：
- frequency: 5.0（X3 的实际扫描频率）
- range_max: 8.0（X3 最大有效探测距离）
- lidar_type: 1（对应 YDLiDAR X3）

#### `ybimu.launch.py` — **新增** YB-IMU 启动文件

关键设计点：通过 ROS 2 的 topic remapping 机制，将 ybimu_node 内部的 `/imu` 话题重映射为 `/imu_sensor_broadcaster/imu`。这是为了**保持与原有 EKF 配置的兼容性**——原来的 ekf.yaml 中 imu0 订阅的是 `/imu_sensor_broadcaster/imu`，替换 IMU 后无需修改 EKF 配置。

**不包含的内容：** YB-IMU 的驱动节点（ybimu_node 可执行文件）未包含在此仓库中。

### PC 侧（pc_stack/）

#### `config/robot_localization/ekf_rf2o.yaml` — **新增** EKF 融合配置

这是整个感知系统的核心。EKF（扩展卡尔曼滤波器）融合三个传感器源：

| 源 | 话题 | 融合分量 | 为什么 |
|---|---|---|---|
| odom0 | `/base_controller/odom` | **vx, vy**（线速度） | 轮式里程计短时精度高，但位置会漂移，所以只取速度 |
| odom1 | `/laser_odom`（rf2o） | **x, y**（位置） | 激光匹配提供无漂移的绝对位置修正 |
| imu0 | `/imu_sensor_broadcaster/imu` | **roll/pitch/yaw + 角速度** | IMU 提供绝对姿态基准，不融合线加速度避免振动噪声 |

特别注意：rf2o 输出的 yaw 航向角**没有**融合进 EKF，因为 IMU 有磁力计校正的绝对航向更稳定。rf2o 只用它的 x/y 位置来修正轮子里程计的漂移。

输出：`/odometry/filtered` 话题（50Hz）+ `odom → base_footprint` TF 变换。

#### `config/slam.yaml` — **新增** SLAM Toolbox 参数

用于在线异步建图模式（online_async）。针对 YDLiDAR X3（5Hz, 8m 量程）和室内场景做了参数整定：
- resolution: 0.05（5cm 栅格，适合室内导航）
- map_update_rate: 2.0
- 扫描匹配参数放宽，兼容 5Hz 低帧率

#### `config/nav2.yaml` — **新增** Nav2 全栈参数

包含：controller_server、planner_server、behavior_server、bt_navigator、velocity_smoother、collision_monitor 等所有 Nav2 节点的参数。

主要适配点：
- 全向底盘（支持 vx, vy, wz 三自由度运动）
- MPPI 控制器参数
- costmap 适配 YDLiDAR X3 的检测范围

#### `launch/pc_slam.launch.py` — **新增** 轻量测试版启动

只启动 rf2o + EKF，适合先验证传感器和融合是否正常工作。

#### `launch/pc_full.launch.py` — **新增** 全栈启动（推荐）

通过 `mode:=slam` 或 `mode:=nav` 参数一键切换建图/导航模式：
- `mode:=slam` → rf2o + EKF + SLAM Toolbox + Rviz2
- `mode:=nav` → rf2o + EKF + SLAM Toolbox + Nav2 全套 + Rviz2

两种模式下 slam_toolbox 都运行——slam 模式用于建图，nav 模式中 slam_toolbox 同时承担定位功能（替代 AMCL）。

---

## TF 坐标树

TF 树是分布式系统中保证数据一致性的关键：

| TF 变换 | 发布者 | 位置 | 说明 |
|---|---|---|---|
| map → odom | SLAM Toolbox | **PC** | 回环检测修正的全局漂移 |
| odom → base_footprint | **EKF** | **PC** | 三源融合后的机器人位姿 |
| base_footprint → base_link → laser_frame | robot_state_publisher | **树莓派** | URDF 定义的静态变换 |

三者**互不冲突**，各司其职：EKF 只发布 odom→base_footprint，SLAM Toolbox 只修正 map→odom。

---

## 启动方式

### 前提条件

两台机器在同一网络，ROS_DOMAIN_ID 一致：

```bash
export ROS_DOMAIN_ID=7
```

### 树莓派 — 硬件驱动

```bash
source ~/lekiwi_ws/install/setup.bash
export ROS_DOMAIN_ID=7
ros2 launch lekiwi_bringup base_complete.launch.py
```

启动后验证：
```bash
ros2 topic list | grep -E "/scan|/odom|/imu_sensor"
```

### PC — 感知 + 导航

```bash
source ~/lekiwi_pc_ws/install/setup.bash
export ROS_DOMAIN_ID=7

# 建图
ros2 launch lekiwi_navigation pc_full.launch.py mode:=slam

# 或导航（需事先建好地图）
ros2 launch lekiwi_navigation pc_full.launch.py mode:=nav
```

### 地图保存

```bash
ros2 run nav2_map_server map_saver_cli -f my_map
```

---

## 依赖的上游项目

| 项目 | 链接 | 在本项目中的角色 |
|---|---|---|
| lekiwi_ros2 | https://github.com/adityakamath/lekiwi_ros2 | 基础 ROS 2 包（bringup/control/description/navigation） |
| rf2o_laser_odometry | https://github.com/MAPIRlab/rf2o_laser_odometry | 激光里程计算法（需使用 ros2 分支，apt 无二进制包需源码编译） |
| slam_toolbox | ROS 2 官方包 | 建图与定位 |
| Nav2 | ROS 2 官方包 | 自主导航栈 |
| robot_localization | ROS 2 官方包 | EKF 传感器融合 |

### 非公开依赖

| 组件 | 说明 |
|---|---|
| ybimu_node | YB-IMU 串口驱动节点，未包含在本仓库中 |
| ydlidar_ros2 或等效驱动 | YDLiDAR X3 ROS 2 驱动，未包含在本仓库中 |

---

## 本仓库包含 vs 不包含

### 包含（我们写的/改的，全部开源可共享）

- `base_complete.launch.py` — 一键启动文件（~30 行 Python）
- `laser.yaml` — YDLiDAR X3 参数配置（~20 行 YAML）
- `ybimu.launch.py` — YB-IMU 启动文件（~50 行 Python）
- `ekf_rf2o.yaml` — EKF 三源融合配置（~80 行 YAML）
- `slam.yaml` — SLAM Toolbox 参数（~60 行 YAML）
- `nav2.yaml` — Nav2 全栈参数（~350 行 YAML）
- `pc_slam.launch.py` — PC 侧轻量启动文件（~50 行 Python）
- `pc_full.launch.py` — PC 侧全栈启动文件（~120 行 Python）

### 不包含（上游项目或非公开代码）

- lekiwi_ros2 完整项目（见上游链接）
- rf2o_laser_odometry 源码（见上游链接）
- ybimu_node 驱动（非公开，请联系作者）
- ydlidar_ros2 驱动（需自行安装）
