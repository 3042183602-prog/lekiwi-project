# PC Stack

PC 侧感知与导航栈配置文件集。

## 文件清单

| 文件 | 说明 |
|---|---|
| `config/robot_localization/ekf_rf2o.yaml` | EKF 三源融合（轮子 vx/vy + rf2o x/y + IMU 姿态/角速度） |
| `config/slam.yaml` | SLAM Toolbox 在线异步建图参数 |
| `config/nav2.yaml` | Nav2 全栈参数 |
| `launch/pc_slam.launch.py` | 轻量版：rf2o + EKF |
| `launch/pc_full.launch.py` | 全栈版：rf2o + EKF + slam_toolbox + Nav2 + Rviz2 |

## 使用方式

参见根目录 README。
