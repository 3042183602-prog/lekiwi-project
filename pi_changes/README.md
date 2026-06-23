# Pi 侧改动概览

## 硬件变更

| 硬件 | 旧 | 新 | 变更内容 |
|---|---|---|---|
| IMU | BNO055（bno055_hardware_interface） | **YB-IMU**（ybimu_node） | 启动文件 + 驱动替换 |
| 激光雷达 | LD19（10Hz, range_max=64.0） | **YDLiDAR X3**（5Hz, range_max=8.0） | laser.yaml 参数重写 |

## 文件说明

| 文件 | 类型 | 说明 |
|---|---|---|
| `base_complete.launch.py` | 新增 | 一键启动底座控制 + YB-IMU + 激光雷达 |
| `laser.yaml` | 修改 | YDLiDAR X3 参数配置 |
| `ybimu.launch.py` | 新增 | YB-IMU 节点启动文件（话题 remap 到 /imu_sensor_broadcaster/imu） |

## 依赖（非公开）

- **ybimu_node** — YB-IMU 串口驱动节点（未包含在此仓库中）
- **YDLiDAR X3 ROS 驱动** — 未包含在此仓库中

## 启动方式

```bash
source ~/lekiwi_ws/install/setup.bash
export ROS_DOMAIN_ID=7
ros2 launch lekiwi_bringup base_complete.launch.py
```
