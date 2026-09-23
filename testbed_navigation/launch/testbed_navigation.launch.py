import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration

def generate_launch_description():
    pkg_testbed_nav = get_package_share_directory('testbed_navigation')
    pkg_testbed_bringup = get_package_share_directory('testbed_bringup')
    default_map_path = os.path.join(pkg_testbed_bringup, 'maps', 'testbed_world.yaml')
    default_amcl_params = os.path.join(pkg_testbed_nav, 'config', 'amcl_params.yaml')
    default_nav2_params = os.path.join(pkg_testbed_nav, 'config', 'nav2_params.yaml')

    use_sim_time = LaunchConfiguration('use_sim_time')
    map_yaml_file = LaunchConfiguration('map')
    amcl_params_file = LaunchConfiguration('amcl_params')
    nav2_params_file = LaunchConfiguration('nav2_params')

    declare_use_sim_time_cmd = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='Use simulation (Gazebo) clock if true'
    )

    declare_map_yaml_cmd = DeclareLaunchArgument(
        'map',
        default_value=default_map_path,
        description='Full path to map yaml file to load'
    )

    declare_amcl_params_cmd = DeclareLaunchArgument(
        'amcl_params',
        default_value=default_amcl_params,
        description='Full path to AMCL parameter file'
    )

    declare_nav2_params_cmd = DeclareLaunchArgument(
        'nav2_params',
        default_value=default_nav2_params,
        description='Full path to Nav2 parameter file'
    )

    map_loader_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_testbed_nav, 'launch', 'map_loader.launch.py')
        ),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'map': map_yaml_file
        }.items()
    )

    localization_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_testbed_nav, 'launch', 'localization.launch.py')
        ),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'params_file': amcl_params_file
        }.items()
    )

    navigation_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_testbed_nav, 'launch', 'navigation.launch.py')
        ),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'params_file': nav2_params_file
        }.items()
    )

    return LaunchDescription([
        declare_use_sim_time_cmd,
        declare_map_yaml_cmd,
        declare_amcl_params_cmd,
        declare_nav2_params_cmd,
        map_loader_cmd,
        localization_cmd,
        navigation_cmd
    ])
