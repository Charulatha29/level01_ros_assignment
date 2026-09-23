# testbed_navigation

Modular Nav2 Navigation Package for the Testbed-T1.0.0 Robot (ROS 2 Humble).

---

## 1. Overview & Architecture

Rather than relying on monolithic bringup scripts, this package builds the ROS 2 Humble Nav2 workflow modularly using individual action servers, lifecycle managers, and plugins. Each component is decoupled, parameterized independently, and capable of being launched standalone or via a unified pipeline:

- **Map Loading Layer**: `nav2_map_server` managed by `nav2_lifecycle_manager`
- **Probabilistic Localization Layer**: `nav2_amcl` (Adaptive Monte Carlo Localization) managed by `nav2_lifecycle_manager`
- **Navigation Action Servers Layer**:
  - `planner_server` running `nav2_navfn_planner/NavfnPlanner` (Global Dijkstra/A* path planning)
  - `controller_server` running `dwb_core::DWBLocalPlanner` (Local trajectory rollout and path tracking)
  - `smoother_server` running `nav2_smoother::SimpleSmoother` (Path smoothing)
  - `behavior_server` running `Spin`, `BackUp`, `DriveOnHeading`, and `Wait` recovery behaviors
  - `bt_navigator` executing replanning and recovery behavior trees
  - Managed by `lifecycle_manager_navigation`

---

## 2. Package Directory Structure

```
testbed_navigation/
├── CMakeLists.txt              # Build configuration and asset installation rules
├── package.xml                 # Package dependencies (nav2 plugins, rclpy, rviz2)
├── README.md                   # Complete implementation report and execution guide
├── config/
│   ├── amcl_params.yaml        # AMCL localization configuration
│   └── nav2_params.yaml        # Planners, controllers, smoothers, costmaps, and BT configs
├── launch/
│   ├── map_loader.launch.py    # Standalone map server launch
│   ├── localization.launch.py  # Standalone AMCL localization launch
│   ├── navigation.launch.py    # Standalone Nav2 action servers launch
│   └── testbed_navigation.launch.py # Master unified launch bringing up all 3 layers
└── rviz/
    └── nav2_default_view.rviz  # Pre-configured RViz display for Nav2 navigation
```

---

## 3. Implementation Approach

### A. Map Loading
- **Plugin**: `nav2_map_server::MapServer`
- **Configuration**: Loads the provided static occupancy grid from `testbed_bringup/maps/testbed_world.yaml`.
- **Lifecycle Management**: Managed by `lifecycle_manager_map_server` configured with `autostart: True`. The map is published on `/map` with `Transient Local` durability so late-joining subscribers (costmaps, RViz) receive the map immediately upon connection.

### B. Robot Localization
- **Plugin**: `nav2_amcl::AmclNode`
- **Configuration**: `config/amcl_params.yaml`
  - Motion Model: Configured for differential drive (`nav2_amcl::DifferentialMotionModel`).
  - Laser Model: Likelihood field matching the planar LiDAR (`/scan`).
  - Initial Pose: Configured to `(x: 0.0, y: 5.0, yaw: 0.0)` matching the Gazebo spawn position in `testbed_playground.world` to ensure immediate particle swarm convergence.
  - Transform Broadcast: Publishes the `map -> odom` transform to close the TF chain.

### C. Navigation Stack & Action Servers
- **Global Path Planning**: `NavfnPlanner` computes optimal paths across the static and obstacle layers.
- **Local Trajectory Controller**: `DWBLocalPlanner` evaluates velocity rollout trajectories `(vx, vtheta)` against trajectory critics: `BaseObstacle`, `PathAlign`, `GoalAlign`, `PathDist`, `GoalDist`, `RotateToGoal`, and `Oscillation`.
- **Costmap Configuration**:
  - **Global Costmap**: `static_layer` (transient local subscription to `/map`), `obstacle_layer` (2D LiDAR ray tracing and marking), and `inflation_layer` (`inflation_radius: 0.55m`, `cost_scaling_factor: 3.0`).
  - **Local Costmap**: 3m × 3m rolling window centered on `base_footprint` with real-time laser obstacle clearing and inflation.
- **Behavior Tree**: `bt_navigator` coordinates path planning, path tracking, obstacle avoidance, and automatic recovery behaviors (spin, backup, wait).

---

## 4. Challenges Faced & Technical Solutions

### Challenge 1: Simulation Clock Mismatch & TF Extrapolation Failures
- **Problem**: Downstream nodes (AMCL, Costmaps, RViz) showed `Message Filter dropping message: ... timestamp is earlier than transform cache` and TF tree broke.
- **Root Cause**: Gazebo publishes simulated time on `/clock`, but some nodes defaulted to wall clock time (`use_sim_time: False`).
- **Solution**: Propagated `use_sim_time: True` across all parameter files (`amcl_params.yaml`, `nav2_params.yaml`), launch files (`map_loader`, `localization`, `navigation`, `testbed_full_bringup`), and RViz node arguments.

### Challenge 2: RViz Map Display QoS Incompatibility
- **Problem**: RViz `/map` display showed `Status: Warn` and failed to render the occupancy grid.
- **Root Cause**: `nav2_map_server` publishes latched map data using `Transient Local` durability and `Reliable` reliability. RViz defaults to `Volatile` durability, missing previously published map updates.
- **Solution**: Updated the RViz Map display properties in `nav2_default_view.rviz` and `full_bringup.rviz` to `Durability Policy: Transient Local` and `Reliability Policy: Reliable`.

### Challenge 3: LiDAR Ray Truncation & Sensor QoS Profile
- **Problem**: In the starter code, the robot failed to see obstacles further than 1.5m away, and sensor subscribers reported QoS incompatibility.
- **Root Cause**: The Gazebo ray sensor max range in `testbed.gazebo` was restricted to 1.5m, and Gazebo's ray plugin outputs `sensor_msgs/LaserScan` with `Best Effort` reliability.
- **Solution**: Extended LiDAR `<max>` range to 12.0m in `testbed.gazebo`, updated costmap raytrace/obstacle ranges to 12m/10m, and configured RViz `/scan` display to `Reliability Policy: Best Effort`.

### Challenge 4: Differential Drive Kinematic Limits & Slippage
- **Problem**: The robot oscillated when executing tight corner turns and approaches.
- **Root Cause**: Default Nav2 controller acceleration limits and angular velocity thresholds were too aggressive for the 0.35m wheelbase.
- **Solution**: Tuned `DWBLocalPlanner` with `max_vel_x: 0.3 m/s`, `acc_lim_x: 2.5 m/s²`, `max_vel_theta: 1.0 rad/s`, and `acc_lim_theta: 3.2 rad/s²` with `RotateToGoal` lookahead scaling for smooth goal alignment.

---

## 5. Execution Guide

### 1. Build and Source Workspace
```bash
cd ~/assignment_ws
colcon build --symlink-install
source install/setup.bash
```

### 2. Launch Simulation Environment (Terminal 1)
```bash
ros2 launch testbed_bringup testbed_full_bringup.launch.py
```
*This starts Gazebo (loading `testbed_playground.world`), spawns the Testbed robot, starts `robot_state_publisher`, and opens RViz.*

### 3. Launch Navigation Stack (Terminal 2)

#### Option A: Unified Bringup (Recommended)
```bash
ros2 launch testbed_navigation testbed_navigation.launch.py
```

#### Option B: Modular Execution (Step-by-Step)
If running each layer independently:
1. **Map Server**:
   ```bash
   ros2 launch testbed_navigation map_loader.launch.py
   ```
2. **AMCL Localization**:
   ```bash
   ros2 launch testbed_navigation localization.launch.py
   ```
3. **Nav2 Action Servers**:
   ```bash
   ros2 launch testbed_navigation navigation.launch.py
   ```

### 4. Sending Navigation Goals in RViz
- Ensure the Fixed Frame is set to `map`.
- Click the **2D Goal Pose** tool in the RViz top toolbar.
- Click and drag anywhere in the free space of the arena.
- Nav2 plans the global path, updates costmaps, and navigates the robot autonomously to the goal pose.
