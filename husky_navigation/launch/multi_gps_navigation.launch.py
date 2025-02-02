# Copyright 2019 Open Source Robotics Foundation, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Author: Darby Lim

import os

import yaml

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, GroupAction, DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, PushRosNamespace
from nav2_common.launch import RewrittenYaml
from launch_ros.descriptions import ParameterFile


robot_names = []
robot_positions = []
with open(os.path.join(get_package_share_directory('husky_navigation'), 'params', 'multirobot_names.yaml'), 'r') as file:
    names = yaml.safe_load(file)
    for i in range(len(names['names'])):
        robot_names.append(names['names'].get('robot'+str(i+1)))
        robot_positions.append(names['position'].get('robot'+str(i+1)))
    
    #ojo a esto porque asi se accede a los valores de un diccionario
    #print(robot_positions[0].get('x'))

def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    autostart = LaunchConfiguration('autostart', default='true')

    lifecycle_nodes=[]

    map_server_config_path_default = os.path.join(
    get_package_share_directory('husky_navigation'),
    'maps',
    'map.yaml'
    )

    map_server_config_path = LaunchConfiguration('map_path', default=map_server_config_path_default)
   
    husky_description_dir = os.path.join(get_package_share_directory('husky_gazebo'), 'launch')
    gps_localization_dir = os.path.join(get_package_share_directory('husky_navigation'), 'launch')
    bringup_dir = os.path.join(get_package_share_directory('husky_navigation'), 'launch')

    params_dir = os.path.join(get_package_share_directory('husky_navigation'), 'params')
    nav2_params_file = os.path.join(params_dir, 'nav2_multirobot_params_1.yaml')

    ekf_params_file = os.path.join(params_dir, 'dual_ekf_navsat_params.yaml')


    ld=LaunchDescription()

    arrNodes=[]


    gazebo_node=IncludeLaunchDescription(
             PythonLaunchDescriptionSource(os.path.join(husky_description_dir,'multirobot.launch.py')),
         )
    arrNodes.append(gazebo_node)


    for i in range(len(robot_names)):

        namespace = robot_names[i]

        map_server_node = Node(
            package='nav2_map_server',
            executable='map_server',
            name=namespace+'_map_server',
            output='screen',
            parameters=[{'use_sim_time': use_sim_time, 
                        'yaml_filename': map_server_config_path,
                        'frame_id': '/map',
                        'topic_name': robot_names[i]+'/map',
                        }],
        )
        arrNodes.append(map_server_node)

        lifecycle_nodes.append(namespace+'_map_server')

        nav2_param_substitutions = {
            'base_frame_id':    robot_names[i]+'/base_footprint',
            'odom_frame_id':    robot_names[i]+'/odom',
            'map_frame_id':     robot_names[i]+'/map',
            'global_frame_id':  robot_names[i]+'/map',
            'robot_base_frame': robot_names[i]+'/base_link',
            'global_frame':     'map',
            'odom_topic':       '/'+robot_names[i]+'/odom',
            'scan_topic':       '/'+robot_names[i]+'/scan',
            'topic':            '/'+robot_names[i]+'/scan',
            }
        
        nav2_configured_params = RewrittenYaml(
            source_file=nav2_params_file,
            root_key='',
            param_rewrites=nav2_param_substitutions,
            convert_types=True)
        

        ekf_param_substitutions = {
            'map_frame':        robot_names[i]+'/map',
            'odom_frame':       robot_names[i]+'/odom',
            'base_link_frame':  robot_names[i]+'/base_link',
            'world_frame':      robot_names[i]+'/map',
            'gps_frame':        robot_names[i]+'/gps',
            'imu_frame':        robot_names[i]+'/imu',
            }
        
        ekf_configured_params=RewrittenYaml(
            source_file=ekf_params_file,
            root_key='',
            param_rewrites=ekf_param_substitutions,
            convert_types=True
        )


        ekf_nav2_action=GroupAction([
            PushRosNamespace(
                namespace=namespace
            ),

            # Navsat transform node for GPS (pendant to be fixed) 
            # IncludeLaunchDescription(
            #     PythonLaunchDescriptionSource(os.path.join(gps_localization_dir,'multi_dual_ekf_navsat.launch.py')),
            #     launch_arguments={
            #         "params_file": ekf_configured_params,
            #         "namespace": namespace,
            #     }.items()
            # ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(bringup_dir,"navigation_launch.py")
                ),
                launch_arguments={
                    'use_sim_time': use_sim_time,
                    "params_file": nav2_configured_params,
                    "autostart": autostart,
                    "namespace": namespace,
                    }.items(),
                             
            ),
        ])
        arrNodes.append(ekf_nav2_action)
    
        map_server_lyfecicle = Node(
            package='nav2_lifecycle_manager',
            executable='lifecycle_manager',
            name='lifecycle_manager',
            output='screen',
            emulate_tty=True,
            parameters=[{'use_sim_time': use_sim_time},
                        {'autostart': autostart},
                        {'node_names': lifecycle_nodes},
                        ]
            )
        arrNodes.append(map_server_lyfecicle)
    

    for node in arrNodes:
        ld.add_action(node)
    
    return ld
